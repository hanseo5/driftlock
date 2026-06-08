#!/usr/bin/env python3
"""Driftlock local harness helpers.

This script intentionally uses only Python's standard library. It validates the
small Driftlock contracts, tracks retry/escalation state, writes handoff objects,
plans Git worktrees, and runs a deterministic dry-run of the closed loop.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PHASES = {
    "spec-lock",
    "task-split",
    "implement",
    "build-test",
    "review",
    "debug",
    "ce",
    "amend",
    "integration",
    "handoff",
}

STATUSES = {"pass", "fail", "blocked", "needs-user", "in-progress"}
CONFIDENCE = {"high", "medium", "low"}
DEFAULT_DEBUG_THRESHOLD = 3
DEFAULT_REVIEW_THRESHOLD = 2
DEFAULT_CE_THRESHOLD = 2


class DriftlockError(Exception):
    """Raised when Driftlock validation fails."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DriftlockError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DriftlockError(f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(non_empty_string(item) for item in value)


def validate_locked_spec_obj(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "id",
        "title",
        "status",
        "intent",
        "goals",
        "non_goals",
        "success_criteria",
        "acceptance_scenarios",
        "decisions",
        "gate_evidence",
    ]
    for key in required:
        require(errors, key in spec, f"locked spec missing required field: {key}")

    require(errors, non_empty_string(spec.get("id")), "locked spec id must be non-empty")
    require(errors, non_empty_string(spec.get("title")), "locked spec title must be non-empty")
    require(errors, spec.get("status") == "locked", "locked spec status must be 'locked'")
    require(
        errors,
        isinstance(spec.get("intent"), str) and len(spec.get("intent", "").strip()) >= 20,
        "locked spec intent must be at least 20 characters",
    )
    require(errors, non_empty_string_list(spec.get("goals")), "locked spec goals must be a non-empty string list")
    require(errors, non_empty_string_list(spec.get("non_goals")), "locked spec non_goals must be a non-empty string list")

    success_criteria = spec.get("success_criteria")
    require(errors, isinstance(success_criteria, list) and bool(success_criteria), "success_criteria must be non-empty")
    seen_sc: set[str] = set()
    if isinstance(success_criteria, list):
        for index, criterion in enumerate(success_criteria):
            prefix = f"success_criteria[{index}]"
            require(errors, isinstance(criterion, dict), f"{prefix} must be an object")
            if not isinstance(criterion, dict):
                continue
            cid = criterion.get("id")
            require(errors, non_empty_string(cid), f"{prefix}.id must be non-empty")
            require(errors, cid not in seen_sc, f"{prefix}.id is duplicated: {cid}")
            if non_empty_string(cid):
                seen_sc.add(cid)
            require(errors, non_empty_string(criterion.get("statement")), f"{prefix}.statement must be non-empty")
            require(errors, criterion.get("testable") is True, f"{prefix}.testable must be true")

    scenarios = spec.get("acceptance_scenarios")
    require(errors, isinstance(scenarios, list) and bool(scenarios), "acceptance_scenarios must be non-empty")
    seen_as: set[str] = set()
    if isinstance(scenarios, list):
        for index, scenario in enumerate(scenarios):
            prefix = f"acceptance_scenarios[{index}]"
            require(errors, isinstance(scenario, dict), f"{prefix} must be an object")
            if not isinstance(scenario, dict):
                continue
            sid = scenario.get("id")
            require(errors, non_empty_string(sid), f"{prefix}.id must be non-empty")
            require(errors, sid not in seen_as, f"{prefix}.id is duplicated: {sid}")
            if non_empty_string(sid):
                seen_as.add(sid)
            for field in ("given", "when", "then"):
                require(errors, non_empty_string(scenario.get(field)), f"{prefix}.{field} must be non-empty")

    decisions = spec.get("decisions")
    require(errors, isinstance(decisions, list) and bool(decisions), "decisions must be non-empty")
    if isinstance(decisions, list):
        seen_decisions: set[str] = set()
        for index, decision in enumerate(decisions):
            prefix = f"decisions[{index}]"
            require(errors, isinstance(decision, dict), f"{prefix} must be an object")
            if not isinstance(decision, dict):
                continue
            did = decision.get("id")
            require(errors, non_empty_string(did), f"{prefix}.id must be non-empty")
            require(errors, did not in seen_decisions, f"{prefix}.id is duplicated: {did}")
            if non_empty_string(did):
                seen_decisions.add(did)
            for field in ("question", "answer", "source"):
                require(errors, non_empty_string(decision.get(field)), f"{prefix}.{field} must be non-empty")

    gate_evidence = spec.get("gate_evidence")
    require(errors, isinstance(gate_evidence, dict), "gate_evidence must be an object")
    if isinstance(gate_evidence, dict):
        for gate in ("intent_gate", "grill_gate", "spec_gate", "analyze_gate"):
            require(errors, gate_evidence.get(gate) == "pass", f"gate_evidence.{gate} must be 'pass'")

    return errors


def spec_cover_ids(spec: dict[str, Any]) -> set[str]:
    success_ids = {item["id"] for item in spec.get("success_criteria", []) if isinstance(item, dict) and "id" in item}
    scenario_ids = {item["id"] for item in spec.get("acceptance_scenarios", []) if isinstance(item, dict) and "id" in item}
    return success_ids | scenario_ids


def validate_task_graph_obj(tasks: dict[str, Any], spec: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    for key in ("spec_id", "status", "tasks"):
        require(errors, key in tasks, f"task graph missing required field: {key}")
    require(errors, non_empty_string(tasks.get("spec_id")), "task graph spec_id must be non-empty")
    require(errors, tasks.get("status") == "ready", "task graph status must be 'ready'")
    if spec is not None:
        require(errors, tasks.get("spec_id") == spec.get("id"), "task graph spec_id must match locked spec id")

    task_list = tasks.get("tasks")
    require(errors, isinstance(task_list, list) and bool(task_list), "tasks must be a non-empty list")
    if not isinstance(task_list, list):
        return errors

    task_ids: set[str] = set()
    for index, task in enumerate(task_list):
        prefix = f"tasks[{index}]"
        require(errors, isinstance(task, dict), f"{prefix} must be an object")
        if not isinstance(task, dict):
            continue
        tid = task.get("id")
        require(errors, non_empty_string(tid), f"{prefix}.id must be non-empty")
        require(errors, tid not in task_ids, f"{prefix}.id is duplicated: {tid}")
        if non_empty_string(tid):
            task_ids.add(tid)
        require(errors, non_empty_string(task.get("title")), f"{prefix}.title must be non-empty")
        require(errors, non_empty_string(task.get("branch")), f"{prefix}.branch must be non-empty")
        require(
            errors,
            non_empty_string_list(task.get("acceptance_criteria")),
            f"{prefix}.acceptance_criteria must be a non-empty string list",
        )
        require(errors, non_empty_string_list(task.get("covers")), f"{prefix}.covers must be a non-empty string list")
        require(errors, isinstance(task.get("dependencies"), list), f"{prefix}.dependencies must be a list")

    for index, task in enumerate(task_list):
        if not isinstance(task, dict):
            continue
        tid = task.get("id")
        deps = task.get("dependencies", [])
        if isinstance(deps, list):
            for dep in deps:
                require(errors, isinstance(dep, str), f"tasks[{index}].dependencies contains a non-string value")
                require(errors, dep in task_ids, f"tasks[{index}].dependencies references missing task: {dep}")
                require(errors, dep != tid, f"tasks[{index}] cannot depend on itself")

    if spec is not None:
        required_covers = spec_cover_ids(spec)
        actual_covers: set[str] = set()
        for task in task_list:
            if isinstance(task, dict) and isinstance(task.get("covers"), list):
                actual_covers.update(item for item in task["covers"] if isinstance(item, str))
        missing = sorted(required_covers - actual_covers)
        unknown = sorted(actual_covers - required_covers)
        require(errors, not missing, f"task split gate missing coverage for: {', '.join(missing)}")
        require(errors, not unknown, f"task split gate has unknown cover ids: {', '.join(unknown)}")

    return errors


def validate_handoff_obj(handoff: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ["id", "task_id", "phase", "status", "attempt", "summary", "evidence", "next_action"]
    for key in required:
        require(errors, key in handoff, f"handoff missing required field: {key}")
    require(errors, non_empty_string(handoff.get("id")), "handoff id must be non-empty")
    require(errors, non_empty_string(handoff.get("task_id")), "handoff task_id must be non-empty")
    require(errors, handoff.get("phase") in PHASES, f"handoff phase must be one of: {', '.join(sorted(PHASES))}")
    require(errors, handoff.get("status") in STATUSES, f"handoff status must be one of: {', '.join(sorted(STATUSES))}")
    require(errors, isinstance(handoff.get("attempt"), int) and handoff.get("attempt", 0) >= 1, "handoff attempt must be >= 1")
    require(errors, non_empty_string(handoff.get("summary")), "handoff summary must be non-empty")
    require(errors, isinstance(handoff.get("evidence"), list), "handoff evidence must be a list")
    if isinstance(handoff.get("evidence"), list):
        require(errors, all(isinstance(item, str) for item in handoff["evidence"]), "handoff evidence entries must be strings")
    require(errors, non_empty_string(handoff.get("next_action")), "handoff next_action must be non-empty")
    if "advisor_confidence" in handoff:
        require(errors, handoff.get("advisor_confidence") in CONFIDENCE, "advisor_confidence must be high, medium, or low")
    if "ce_instructions" in handoff:
        require(errors, isinstance(handoff.get("ce_instructions"), str), "ce_instructions must be a string")
    return errors


def fail_if_errors(errors: list[str]) -> None:
    if errors:
        raise DriftlockError("\n".join(f"- {error}" for error in errors))


def make_handoff(
    handoff_id: str,
    task_id: str,
    phase: str,
    status: str,
    attempt: int,
    summary: str,
    evidence: list[str],
    next_action: str,
    ce_instructions: str | None = None,
    advisor_confidence: str | None = None,
) -> dict[str, Any]:
    handoff: dict[str, Any] = {
        "id": handoff_id,
        "task_id": task_id,
        "phase": phase,
        "status": status,
        "attempt": attempt,
        "summary": summary,
        "evidence": evidence,
        "next_action": next_action,
    }
    if ce_instructions is not None:
        handoff["ce_instructions"] = ce_instructions
    if advisor_confidence is not None:
        handoff["advisor_confidence"] = advisor_confidence
    fail_if_errors(validate_handoff_obj(handoff))
    return handoff


def new_state(task_id: str) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "debug_attempts": 0,
        "ce_cycles": 0,
        "review_rejects": 0,
        "status": "in-progress",
        "history": [],
    }


def apply_state_event(
    state: dict[str, Any],
    event: str,
    evidence: str,
    debug_threshold: int = DEFAULT_DEBUG_THRESHOLD,
    review_threshold: int = DEFAULT_REVIEW_THRESHOLD,
    ce_threshold: int = DEFAULT_CE_THRESHOLD,
) -> dict[str, Any]:
    state = dict(state)
    state.setdefault("history", [])
    route = "continue"

    if event == "build-fail":
        state["debug_attempts"] = int(state.get("debug_attempts", 0)) + 1
        route = "ce" if state["debug_attempts"] >= debug_threshold else "debug"
        state["status"] = "needs-ce" if route == "ce" else "needs-debug"
    elif event == "build-pass":
        state["status"] = "needs-review"
        route = "review"
    elif event == "review-reject":
        state["review_rejects"] = int(state.get("review_rejects", 0)) + 1
        route = "ce" if state["review_rejects"] >= review_threshold else "implement"
        state["status"] = "needs-ce" if route == "ce" else "needs-fix"
    elif event == "review-pass":
        state["status"] = "task-gate-pass"
        route = "merge-or-integrate"
    elif event == "ce-cycle":
        state["ce_cycles"] = int(state.get("ce_cycles", 0)) + 1
        route = "needs-user" if state["ce_cycles"] >= ce_threshold else "implement"
        state["status"] = "needs-user" if route == "needs-user" else "needs-fix"
    elif event == "spec-conflict":
        state["status"] = "needs-amendment"
        route = "amend"
    elif event == "integration-pass":
        state["status"] = "ready-for-final-handoff"
        route = "handoff"
    else:
        raise DriftlockError(f"Unknown state event: {event}")

    state["last_route"] = route
    state["history"].append({"at": utc_now(), "event": event, "route": route, "evidence": evidence})
    return state


def advisor_route(issue: str, simulate: str | None = None) -> dict[str, Any]:
    if simulate == "claude-available":
        return {
            "issue": issue,
            "primary": "claude",
            "primary_status": "available",
            "fallback": "not-used",
            "advisor_confidence": "medium",
            "requires_user_approval": True,
            "recommendation": "Use Claude for independent feasibility review before user approval.",
        }
    if simulate == "claude-limit":
        return {
            "issue": issue,
            "primary": "claude",
            "primary_status": "limit-or-unavailable",
            "fallback": "codex-second-pass",
            "advisor_confidence": "medium",
            "requires_user_approval": True,
            "recommendation": "Use Codex second-pass advisory and keep user approval required.",
        }
    if simulate == "codex-second-pass":
        return {
            "issue": issue,
            "primary": "codex",
            "primary_status": "available",
            "fallback": "local-evidence",
            "advisor_confidence": "medium",
            "requires_user_approval": True,
            "recommendation": "Use Codex second-pass advisory because primary advisor is unavailable.",
        }

    claude = shutil.which("claude")
    codex = shutil.which("codex")
    if claude:
        return {
            "issue": issue,
            "primary": "claude",
            "primary_status": "available",
            "primary_path": claude,
            "fallback": "codex-second-pass" if codex else "local-evidence",
            "advisor_confidence": "medium",
            "requires_user_approval": True,
            "recommendation": "Run Claude advisory for independent review; user still approves product intent.",
        }
    if codex:
        return {
            "issue": issue,
            "primary": "codex",
            "primary_status": "available",
            "primary_path": codex,
            "fallback": "local-evidence",
            "advisor_confidence": "medium",
            "requires_user_approval": True,
            "recommendation": "Run Codex second-pass advisory; user still approves product intent.",
        }
    return {
        "issue": issue,
        "primary": "local-evidence",
        "primary_status": "no-model-cli-found",
        "fallback": "needs-user",
        "advisor_confidence": "low",
        "requires_user_approval": True,
        "recommendation": "Do not auto-approve. Summarize evidence and ask the user.",
    }


def branch_path_safe(value: str) -> str:
    allowed = []
    for char in value.lower().strip():
        if char.isalnum():
            allowed.append(char)
        elif char in ("-", "_", "/", "."):
            allowed.append(char)
        elif char.isspace():
            allowed.append("-")
    cleaned = "".join(allowed).strip("-")
    return cleaned or "task"


def worktree_plan(tasks: dict[str, Any], repo: Path, worktrees_dir: Path) -> dict[str, Any]:
    plan = []
    for task in tasks.get("tasks", []):
        branch = branch_path_safe(task["branch"])
        worktree_path = worktrees_dir / task["id"]
        plan.append(
            {
                "task_id": task["id"],
                "branch": branch,
                "worktree": str(worktree_path),
                "create_command": ["git", "-C", str(repo), "worktree", "add", "-b", branch, str(worktree_path), "HEAD"],
            }
        )
    return {"repo": str(repo), "worktrees_dir": str(worktrees_dir), "tasks": plan}


def ensure_git_repo(repo: Path) -> None:
    result = subprocess.run(["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
    if result.returncode != 0:
        raise DriftlockError(f"Not a Git repository: {repo}")


def create_worktrees(plan: dict[str, Any]) -> None:
    for item in plan["tasks"]:
        worktree = Path(item["worktree"])
        if worktree.exists():
            continue
        result = subprocess.run(item["create_command"], capture_output=True, text=True)
        if result.returncode != 0:
            raise DriftlockError(f"Failed to create worktree for {item['task_id']}:\n{result.stderr.strip()}")


def fake_locked_spec() -> dict[str, Any]:
    return {
        "id": "dryrun-spec",
        "title": "Dry Run Product Flow",
        "status": "locked",
        "intent": "Build a local feature flow that proves Driftlock can lock intent before implementation starts.",
        "goals": ["Demonstrate closed-loop execution with gates and evidence."],
        "non_goals": ["Do not create a production remote or publish packages."],
        "success_criteria": [
            {"id": "SC1", "statement": "The task split covers the primary flow.", "testable": True},
            {"id": "SC2", "statement": "Final handoff happens only after gates pass.", "testable": True},
        ],
        "acceptance_scenarios": [
            {
                "id": "AS1",
                "given": "A locked spec exists.",
                "when": "Tasks are generated.",
                "then": "Every success criterion and scenario is covered.",
            },
            {
                "id": "AS2",
                "given": "A task fails build and review.",
                "when": "The harness routes the failure.",
                "then": "Debug, CE, amendment, and final handoff gates happen in order.",
            },
        ],
        "decisions": [
            {
                "id": "D1",
                "question": "Should CE always run?",
                "answer": "No. CE is conditional and activates only on threshold signals.",
                "source": "grill-me",
            }
        ],
        "gate_evidence": {
            "intent_gate": "pass",
            "grill_gate": "pass",
            "spec_gate": "pass",
            "analyze_gate": "pass",
        },
    }


def fake_tasks() -> dict[str, Any]:
    return {
        "spec_id": "dryrun-spec",
        "status": "ready",
        "tasks": [
            {
                "id": "T1",
                "title": "Implement gated workflow state",
                "branch": "task/gated-workflow-state",
                "acceptance_criteria": ["SC1 and AS1 are covered by validated task metadata."],
                "covers": ["SC1", "AS1"],
                "dependencies": [],
            },
            {
                "id": "T2",
                "title": "Finalize closed-loop handoff",
                "branch": "task/final-handoff-gate",
                "acceptance_criteria": ["SC2 and AS2 pass after simulated failure recovery."],
                "covers": ["SC2", "AS2"],
                "dependencies": ["T1"],
            },
        ],
    }


def run_dry_run(out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    spec = fake_locked_spec()
    tasks = fake_tasks()
    fail_if_errors(validate_locked_spec_obj(spec))
    fail_if_errors(validate_task_graph_obj(tasks, spec))

    write_json(out_dir / "locked-spec.json", spec)
    write_json(out_dir / "tasks.json", tasks)

    state = new_state("T2")
    handoffs = []
    trace = [
        {"step": "locked-spec", "gate": "pass"},
        {"step": "task-split", "gate": "pass"},
    ]

    handoffs.append(
        make_handoff(
            "H1",
            "T2",
            "build-test",
            "fail",
            1,
            "Simulated build failure.",
            ["build command exited non-zero"],
            "Route to Debug Mode.",
            advisor_confidence="medium",
        )
    )
    state = apply_state_event(state, "build-fail", "build failed", debug_threshold=3)
    trace.append({"step": "build-test", "gate": "fail", "route": state["last_route"]})

    handoffs.append(
        make_handoff(
            "H2",
            "T2",
            "debug",
            "pass",
            1,
            "Debug Mode produced a local fix brief.",
            ["missing dependency diagnosed"],
            "Return to implementer/fixer.",
        )
    )
    state = apply_state_event(state, "build-pass", "build fixed")
    trace.append({"step": "debug", "gate": "pass", "route": state["last_route"]})

    handoffs.append(
        make_handoff(
            "H3",
            "T2",
            "review",
            "fail",
            1,
            "Simulated review reject due to structural issue.",
            ["review rejected state transition ownership"],
            "Route to CE after reject threshold.",
        )
    )
    state = apply_state_event(state, "review-reject", "review rejected structural issue", review_threshold=1)
    trace.append({"step": "review", "gate": "fail", "route": state["last_route"]})

    handoffs.append(
        make_handoff(
            "H4",
            "T2",
            "ce",
            "pass",
            1,
            "CE wrote a fix brief and learning note.",
            ["root cause identified", "prevention note written"],
            "Return to implementer/fixer.",
            ce_instructions="Keep review read-only; route code changes back to implementer/fixer.",
        )
    )
    state = apply_state_event(state, "ce-cycle", "CE fix brief produced", ce_threshold=2)
    trace.append({"step": "ce", "gate": "pass", "route": state["last_route"]})

    advisor_results = [
        advisor_route("Spec conflict dry-run: primary available path.", "claude-available"),
        advisor_route("Spec conflict dry-run: Claude usage limit path.", "claude-limit"),
        advisor_route("Spec conflict dry-run: Codex second-pass path.", "codex-second-pass"),
    ]
    handoffs.append(
        make_handoff(
            "H5",
            "T2",
            "amend",
            "needs-user",
            1,
            "Simulated spec conflict requires user-approved amendment.",
            ["advisor fallback matrix generated", "low confidence cannot auto-approve"],
            "Ask user to approve or reject the amendment.",
            advisor_confidence="medium",
        )
    )
    state = apply_state_event(state, "spec-conflict", "simulated spec ambiguity")
    trace.append({"step": "amendment-advisor", "gate": "needs-user", "route": state["last_route"]})

    handoffs.append(
        make_handoff(
            "H6",
            "T2",
            "integration",
            "pass",
            2,
            "Simulated user approval, re-lock, build, review, and integration all passed.",
            ["amendment approved in dry-run", "integration gate passed"],
            "Produce final handoff.",
            advisor_confidence="high",
        )
    )
    state = apply_state_event(state, "integration-pass", "all gates passed")
    trace.append({"step": "integration", "gate": "pass", "route": state["last_route"]})

    final_handoff = make_handoff(
        "H7",
        "all",
        "handoff",
        "pass",
        1,
        "Final handoff produced only after spec, task split, build/test, review, CE, amendment, and integration gates passed.",
        ["locked spec valid", "task split valid", "failure routes exercised", "integration gate passed"],
        "Deliver result.",
        advisor_confidence="high",
    )
    handoffs.append(final_handoff)

    for handoff in handoffs:
        fail_if_errors(validate_handoff_obj(handoff))

    learning_note = """# Learning Note: Review Reject Returned To Implementer

## Trigger

Review rejected the task because state transition ownership was unclear.

## Root Cause

The workflow treated review as if it could perform fixes.

## Fix Brief

Keep review read-only and route CE output back to implementer/fixer before build/test.

## Prevention

Task gates must verify the path CE -> implementer/fixer -> build/test -> review.
"""
    write_text(out_dir / "learning-note.md", learning_note)
    write_json(out_dir / "state.json", state)
    write_json(out_dir / "advisor-results.json", {"results": advisor_results})
    write_json(out_dir / "handoffs.json", {"handoffs": handoffs})
    write_json(out_dir / "final-handoff.json", final_handoff)
    result = {
        "status": "pass",
        "out_dir": str(out_dir),
        "trace": trace,
        "advisor_paths": [item["primary"] + ":" + item["primary_status"] for item in advisor_results],
        "final_handoff_after_all_gates": True,
        "artifacts": [
            "locked-spec.json",
            "tasks.json",
            "handoffs.json",
            "advisor-results.json",
            "state.json",
            "learning-note.md",
            "final-handoff.json",
        ],
    }
    write_json(out_dir / "dry-run-summary.json", result)
    return result


def command_validate(args: argparse.Namespace) -> dict[str, Any]:
    if args.kind == "locked-spec":
        spec = read_json(Path(args.path))
        fail_if_errors(validate_locked_spec_obj(spec))
    elif args.kind == "tasks":
        tasks = read_json(Path(args.path))
        spec = read_json(Path(args.spec)) if args.spec else None
        fail_if_errors(validate_task_graph_obj(tasks, spec))
    elif args.kind == "handoff":
        handoff = read_json(Path(args.path))
        fail_if_errors(validate_handoff_obj(handoff))
    else:
        raise DriftlockError(f"Unknown validation kind: {args.kind}")
    return {"status": "pass", "kind": args.kind, "path": args.path}


def command_handoff(args: argparse.Namespace) -> dict[str, Any]:
    handoff = make_handoff(
        args.id,
        args.task_id,
        args.phase,
        args.status,
        args.attempt,
        args.summary,
        args.evidence or [],
        args.next_action,
        ce_instructions=args.ce_instructions,
        advisor_confidence=args.advisor_confidence,
    )
    write_json(Path(args.out), handoff)
    return {"status": "pass", "path": args.out, "handoff": handoff}


def command_track(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.state)
    state = read_json(path) if path.exists() else new_state(args.task_id)
    state = apply_state_event(
        state,
        args.event,
        args.evidence,
        debug_threshold=args.debug_threshold,
        review_threshold=args.review_threshold,
        ce_threshold=args.ce_threshold,
    )
    out = Path(args.out) if args.out else path
    write_json(out, state)
    return {"status": "pass", "path": str(out), "route": state["last_route"], "state": state}


def command_advisor(args: argparse.Namespace) -> dict[str, Any]:
    issue = args.issue
    if args.issue_file:
        issue = Path(args.issue_file).read_text(encoding="utf-8")
    return advisor_route(issue, args.simulate)


def command_worktree_plan(args: argparse.Namespace) -> dict[str, Any]:
    tasks = read_json(Path(args.tasks))
    fail_if_errors(validate_task_graph_obj(tasks))
    repo = Path(args.repo).resolve()
    if args.ensure_repo:
        ensure_git_repo(repo)
    plan = worktree_plan(tasks, repo, Path(args.worktrees).resolve())
    if args.create:
        ensure_git_repo(repo)
        create_worktrees(plan)
        plan["created"] = True
    if args.out:
        write_json(Path(args.out), plan)
    return {"status": "pass", "plan": plan}


def command_dry_run(args: argparse.Namespace) -> dict[str, Any]:
    return run_dry_run(Path(args.out))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Driftlock local harness helpers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate Driftlock JSON artifacts")
    validate.add_argument("kind", choices=["locked-spec", "tasks", "handoff"])
    validate.add_argument("path")
    validate.add_argument("--spec", help="Locked Spec path for task coverage validation")
    validate.set_defaults(func=command_validate)

    handoff = subparsers.add_parser("handoff", help="Write and validate a handoff object")
    handoff.add_argument("--out", required=True)
    handoff.add_argument("--id", required=True)
    handoff.add_argument("--task-id", required=True)
    handoff.add_argument("--phase", required=True, choices=sorted(PHASES))
    handoff.add_argument("--status", required=True, choices=sorted(STATUSES))
    handoff.add_argument("--attempt", type=int, required=True)
    handoff.add_argument("--summary", required=True)
    handoff.add_argument("--evidence", action="append")
    handoff.add_argument("--next-action", required=True)
    handoff.add_argument("--ce-instructions")
    handoff.add_argument("--advisor-confidence", choices=sorted(CONFIDENCE))
    handoff.set_defaults(func=command_handoff)

    track = subparsers.add_parser("track", help="Apply a retry/escalation event to state")
    track.add_argument("--state", required=True)
    track.add_argument("--task-id", default="T1")
    track.add_argument("--event", required=True, choices=[
        "build-fail",
        "build-pass",
        "review-reject",
        "review-pass",
        "ce-cycle",
        "spec-conflict",
        "integration-pass",
    ])
    track.add_argument("--evidence", required=True)
    track.add_argument("--out")
    track.add_argument("--debug-threshold", type=int, default=DEFAULT_DEBUG_THRESHOLD)
    track.add_argument("--review-threshold", type=int, default=DEFAULT_REVIEW_THRESHOLD)
    track.add_argument("--ce-threshold", type=int, default=DEFAULT_CE_THRESHOLD)
    track.set_defaults(func=command_track)

    advisor = subparsers.add_parser("advisor", help="Resolve advisor routing with Claude/Codex fallback")
    advisor.add_argument("--issue", default="")
    advisor.add_argument("--issue-file")
    advisor.add_argument("--simulate", choices=["claude-available", "claude-limit", "codex-second-pass"])
    advisor.set_defaults(func=command_advisor)

    worktree = subparsers.add_parser("worktree-plan", help="Create a Git worktree plan for tasks")
    worktree.add_argument("tasks")
    worktree.add_argument("--repo", default=".")
    worktree.add_argument("--worktrees", default=".driftlock/worktrees")
    worktree.add_argument("--out")
    worktree.add_argument("--ensure-repo", action="store_true")
    worktree.add_argument("--create", action="store_true")
    worktree.set_defaults(func=command_worktree_plan)

    dry_run = subparsers.add_parser("dry-run", help="Run a deterministic Driftlock closed-loop dry-run")
    dry_run.add_argument("--out", default=".driftlock/dry-run")
    dry_run.set_defaults(func=command_dry_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
    except DriftlockError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
