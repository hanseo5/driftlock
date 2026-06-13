"""Execution engine: worktrees, task state, execution plan, agent dispatch."""
from __future__ import annotations

import argparse
import re
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from .builders import *  # noqa: F401,F403
from .runner import *  # noqa: F401,F403


def branch_path_safe(value: str) -> str:
    allowed = []
    for char in value.lower().strip():
        if char.isalnum():
            allowed.append(char)
        elif char in ("-", "_", "/", "."):
            allowed.append(char)
        elif char.isspace():
            allowed.append("-")
    return "".join(allowed).strip("-") or "task"


def ensure_git_repo(repo: Path) -> None:
    result = subprocess.run(["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
    if result.returncode != 0:
        raise LodestarError(f"Not a Git repository: {repo}")


def worktree_plan(task_graph: dict[str, Any], repo: Path, worktrees_dir: Path) -> dict[str, Any]:
    plan = []
    for task in task_graph.get("tasks", []):
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


def create_worktrees(plan: dict[str, Any]) -> None:
    for item in plan["tasks"]:
        worktree = Path(item["worktree"])
        if worktree.exists():
            continue
        result = subprocess.run(item["create_command"], capture_output=True, text=True)
        if result.returncode != 0:
            raise LodestarError(f"Failed to create worktree for {item['task_id']}:\n{result.stderr.strip()}")


def task_state_path(run_dir: Path, task_id: str) -> Path:
    return run_dir / "tasks" / task_id / "state.json"


def new_task_state(task: dict[str, Any], run_id: str, spec_id: str, worktree: Path) -> dict[str, Any]:
    state = {
        "run_id": run_id,
        "spec_id": spec_id,
        "task_id": task["id"],
        "title": task["title"],
        "branch": branch_path_safe(task["branch"]),
        "role": task["role"],
        "state": "TASK_READY",
        "status": "ready",
        "worktree": str(worktree),
        "covers": task["covers"],
        "dependencies": task.get("dependencies", []),
        "acceptance_criteria": task["acceptance_criteria"],
        "parallel_group": task_parallel_group(task),
        "write_scope": task_write_scope(task),
        "merge_risk": task_merge_risk(task),
        "attempts": {
            "implementation_attempts": 0,
            "build_attempts": 0,
            "review_attempts": 0,
            "fix_attempts": 0,
            "ce_cycles": 0,
        },
        "gates": dict(TASK_GATE_DEFAULTS),
        "next_allowed_events": task_allowed_events("TASK_READY"),
        "history": [],
    }
    fail_if_errors(validate_task_state_obj(state))
    return state


def execution_task_summary(task_state: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    task_id = task_state["task_id"]
    return {
        "task_id": task_id,
        "title": task_state["title"],
        "branch": task_state["branch"],
        "role": task_state["role"],
        "state": task_state["state"],
        "status": task_state["status"],
        "worktree": task_state["worktree"],
        "state_path": str(task_state_path(run_dir, task_id)),
        "dependencies": task_state.get("dependencies", []),
        "covers": task_state.get("covers", []),
        "parallel_group": task_state.get("parallel_group", "default"),
        "write_scope": task_state.get("write_scope", [task_state["branch"]]),
        "merge_risk": task_state.get("merge_risk", "medium"),
        "attempts": task_state.get("attempts", {}),
        "gates": task_state.get("gates", {}),
        "next_allowed_events": task_state.get("next_allowed_events", []),
    }


def execution_status_from_states(task_states: list[dict[str, Any]]) -> str:
    if any(task["status"] == "blocked" for task in task_states):
        return "blocked"
    if all(task["status"] == "done" for task in task_states):
        return "done"
    if any(task["status"] == "in-progress" for task in task_states):
        return "in-progress"
    return "ready"


def execution_metrics(task_states: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "ready": sum(1 for task in task_states if task["status"] == "ready"),
        "in_progress": sum(1 for task in task_states if task["status"] == "in-progress"),
        "done": sum(1 for task in task_states if task["status"] == "done"),
        "blocked": sum(1 for task in task_states if task["status"] == "blocked"),
        "total": len(task_states),
    }


def build_execution_plan(run_id: str, spec_id: str, run_dir: Path, task_states: list[dict[str, Any]]) -> dict[str, Any]:
    plan = {
        "run_id": run_id,
        "spec_id": spec_id,
        "status": execution_status_from_states(task_states),
        "upstream_source": {
            "repo": "superpowers",
            "adapter": "lodestar-execution-loop",
            "paths": [
                "third_party/upstream/superpowers/skills/subagent-driven-development",
                "third_party/upstream/superpowers/skills/using-git-worktrees",
                "third_party/upstream/superpowers/skills/verification-before-completion",
            ],
        },
        "task_count": len(task_states),
        "tasks": [execution_task_summary(task_state, run_dir) for task_state in task_states],
        "metrics": execution_metrics(task_states),
    }
    fail_if_errors(validate_execution_plan_obj(plan))
    return plan


def write_task_state(run_dir: Path, task_state: dict[str, Any]) -> None:
    fail_if_errors(validate_task_state_obj(task_state))
    write_json(task_state_path(run_dir, task_state["task_id"]), task_state)


def read_task_state(run_dir: Path, task_id: str) -> dict[str, Any]:
    state = read_json(task_state_path(run_dir, task_id))
    fail_if_errors(validate_task_state_obj(state))
    return state


def read_all_task_states(run_dir: Path) -> list[dict[str, Any]]:
    tasks_dir = run_dir / "tasks"
    if not tasks_dir.exists():
        raise LodestarError(f"No task states found in {tasks_dir}")
    states = []
    for state_file in sorted(tasks_dir.glob("*/state.json")):
        state = read_json(state_file)
        fail_if_errors(validate_task_state_obj(state))
        states.append(state)
    if not states:
        raise LodestarError(f"No task states found in {tasks_dir}")
    return states


def write_execution_plan(run_dir: Path, task_states: list[dict[str, Any]]) -> dict[str, Any]:
    run_id = task_states[0]["run_id"]
    spec_id = task_states[0]["spec_id"]
    plan = build_execution_plan(run_id, spec_id, run_dir, task_states)
    write_json(run_dir / "execution-plan.json", plan)
    return plan


def init_execution_run(
    task_graph: dict[str, Any],
    spec: dict[str, Any],
    run_dir: Path,
    repo: Path,
    worktrees_dir: Path,
    run_id: str,
) -> dict[str, Any]:
    fail_if_errors(validate_task_graph_obj(task_graph, spec))
    run_dir.mkdir(parents=True, exist_ok=True)
    if not worktrees_dir.is_absolute():
        worktrees_dir = repo / worktrees_dir
    task_states = []
    for task in task_graph["tasks"]:
        state = new_task_state(task, run_id, spec["id"], worktrees_dir / task["id"])
        write_task_state(run_dir, state)
        task_states.append(state)
    return {"status": "pass", "run_id": run_id, "run_dir": str(run_dir), "execution_plan": write_execution_plan(run_dir, task_states)}


def apply_task_event(task_state: dict[str, Any], event: str, evidence: str, artifact: str | None = None) -> dict[str, Any]:
    current = task_state["state"]
    key = (current, event)
    if key not in TASK_TRANSITIONS:
        raise LodestarError(f"Invalid task transition: {task_state['task_id']} {current} + {event}")
    next_state, status, attempt_key = TASK_TRANSITIONS[key]
    updated = dict(task_state)
    updated["state"] = next_state
    updated["status"] = status
    updated["next_allowed_events"] = task_allowed_events(next_state)
    updated["attempts"] = dict(task_state["attempts"])
    updated["gates"] = {**TASK_GATE_DEFAULTS, **dict(task_state["gates"])}
    updated["history"] = list(task_state.get("history", []))
    if attempt_key:
        updated["attempts"][attempt_key] += 1
    if event == "implementation-ready":
        updated["gates"]["implementation"] = "pass"
    elif event == "implementation-blocked":
        updated["gates"]["implementation"] = "fail"
    elif event == "build-pass":
        updated["gates"]["build"] = "pass"
    elif event == "build-fail":
        updated["gates"]["build"] = "fail"
    elif event == "reviewer-approve":
        updated["gates"]["review"] = "pass"
    elif event == "reviewer-reject":
        updated["gates"]["review"] = "fail"
    elif event == "merge-pass":
        updated["gates"]["merge"] = "pass"
    elif event == "merge-conflict":
        updated["gates"]["merge"] = "fail"
    elif event == "ce-needed":
        updated["gates"]["ce"] = "pending"
    elif event == "debrief-brief-ready":
        updated["gates"]["ce"] = "pass"
    elif event == "amendment-needed":
        updated["gates"]["amendment"] = "pending"
    elif event == "amendment-approved":
        updated["gates"]["amendment"] = "pass"
    updated["history"].append(
        {
            "at": utc_now(),
            "event": event,
            "from": current,
            "to": next_state,
            "evidence": evidence,
            "artifact": artifact,
        }
    )
    fail_if_errors(validate_task_state_obj(updated))
    return updated


def states_by_task_id(task_states: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {task_state["task_id"]: task_state for task_state in task_states}


def pending_dependencies(task_state: dict[str, Any], task_states: list[dict[str, Any]]) -> list[str]:
    by_id = states_by_task_id(task_states)
    pending = []
    for dep in task_state.get("dependencies", []):
        dep_state = by_id.get(dep)
        if dep_state is None or dep_state.get("state") != "TASK_DONE":
            pending.append(dep)
    return pending


def select_next_execution_task(task_states: list[dict[str, Any]]) -> dict[str, Any]:
    active_states = {"IMPLEMENTING", "BUILDING", "REVIEWING", "FIXING", "COMPOUNDING", "AMENDMENT_PENDING"}
    active = [task for task in task_states if task["state"] in active_states]
    if active:
        task = sorted(active, key=lambda item: item["task_id"])[0]
        return {
            "status": "ready",
            "reason": "existing task is already inside the execution loop",
            "task_id": task["task_id"],
            "state": task["state"],
            "pending_dependencies": [],
        }

    ready = [task for task in task_states if task["state"] == "TASK_READY" and not pending_dependencies(task, task_states)]
    if ready:
        task = sorted(ready, key=lambda item: item["task_id"])[0]
        return {
            "status": "ready",
            "reason": "task dependencies are satisfied",
            "task_id": task["task_id"],
            "state": task["state"],
            "pending_dependencies": [],
        }

    if all(task["state"] == "TASK_DONE" for task in task_states):
        return {
            "status": "complete",
            "reason": "all tasks are done",
            "task_id": None,
            "state": "TASK_DONE",
            "pending_dependencies": [],
        }

    blocked_candidates = []
    for task in task_states:
        if task["state"] == "TASK_READY":
            blocked_candidates.append(
                {
                    "task_id": task["task_id"],
                    "pending_dependencies": pending_dependencies(task, task_states),
                }
            )
    return {
        "status": "blocked",
        "reason": "no task is runnable until dependencies complete",
        "task_id": None,
        "state": "TASK_BLOCKED",
        "pending_dependencies": blocked_candidates,
    }


def dispatch_artifact_path(run_dir: Path, task_id: str) -> Path:
    return run_dir / "dispatch" / f"{task_id}-agent-dispatch.json"


def build_agent_dispatch(
    run_dir: Path,
    task_state: dict[str, Any],
    mode: str,
    spec_path: str,
    task_graph_path: str,
) -> dict[str, Any]:
    state = task_state["state"]
    if state not in EXECUTION_ROUTE_BY_STATE:
        raise LodestarError(f"Task {task_state['task_id']} is not dispatchable from state {state}")
    route = dict(EXECUTION_ROUTE_BY_STATE[state])
    route["current_state"] = state
    dispatch = {
        "dispatch_id": f"{task_state['run_id']}-{task_state['task_id']}-{route['role']}",
        "created_at": utc_now(),
        "run_id": task_state["run_id"],
        "spec_id": task_state["spec_id"],
        "status": "ready",
        "mode": mode,
        "route": route,
        "task": {
            "task_id": task_state["task_id"],
            "title": task_state["title"],
            "branch": task_state["branch"],
            "worktree": task_state["worktree"],
            "covers": task_state["covers"],
            "dependencies": task_state.get("dependencies", []),
            "acceptance_criteria": task_state["acceptance_criteria"],
            "parallel_group": task_state.get("parallel_group", "default"),
            "write_scope": task_state.get("write_scope", [task_state["branch"]]),
            "merge_risk": task_state.get("merge_risk", "medium"),
            "attempts": task_state["attempts"],
            "gates": task_state["gates"],
            "history": task_state.get("history", []),
        },
        "input_artifacts": {
            "locked_spec": spec_path,
            "task_graph": task_graph_path,
            "execution_plan": str(run_dir / "execution-plan.json"),
            "task_state": str(task_state_path(run_dir, task_state["task_id"])),
        },
        "upstream_source": {
            "repo": "superpowers",
            "paths": [
                "third_party/upstream/superpowers/skills/executing-plans",
                "third_party/upstream/superpowers/skills/subagent-driven-development",
                "third_party/upstream/superpowers/skills/test-driven-development",
                "third_party/upstream/superpowers/skills/systematic-debugging",
                "third_party/upstream/superpowers/skills/using-git-worktrees",
                "third_party/upstream/superpowers/skills/verification-before-completion",
            ],
        },
        "execution_policy": {
            "spec_complete_means_sdd_ready": True,
            "dispatch_after_task_split": True,
            "tdd_required": True,
            "builder_required": True,
            "reviewer_read_only": True,
            "user_owns_product_intent": True,
            "ce_forbidden_routes": sorted(CE_FORBIDDEN_ROUTES),
            "ce_return_routes": sorted(CE_RETURN_ROUTES),
        },
        "instructions": [
            "Work only on the assigned task and preserve the Locked Spec.",
            "Start from a failing or targeted test when practical; otherwise record why test-first is not applicable and define concrete verification before editing.",
            "Do not skip builder evidence or read-only review.",
            "Route product-intent, UX-lock, safety, cost, or scope changes to amendment advisor instead of deciding silently.",
            "After CE synthesis, return through fixer or implementer before builder and reviewer.",
        ],
        "expected_events": route["expected_events"],
    }
    fail_if_errors(validate_agent_dispatch_obj(dispatch))
    return dispatch


def dispatch_next_execution_task(
    run_dir: Path,
    mode: str,
    spec_path: str,
    task_graph_path: str,
    out_path: Path | None = None,
) -> dict[str, Any]:
    if mode not in EXECUTION_DISPATCH_MODES:
        raise LodestarError(f"Unknown execution dispatch mode: {mode}")
    task_states = read_all_task_states(run_dir)
    decision = select_next_execution_task(task_states)
    if decision["status"] != "ready":
        plan = write_execution_plan(run_dir, task_states)
        return {"status": decision["status"], "decision": decision, "execution_plan": plan}

    task_id = decision["task_id"]
    assert task_id is not None
    state = read_task_state(run_dir, task_id)
    artifact_path = out_path or dispatch_artifact_path(run_dir, task_id)
    auto_event = None
    if state["state"] == "TASK_READY":
        auto_event = "implementation-started"
        state = apply_task_event(
            state,
            auto_event,
            "execution driver dispatched the first runnable implementer task",
            str(artifact_path),
        )
        write_task_state(run_dir, state)

    dispatch = build_agent_dispatch(run_dir, state, mode, spec_path, task_graph_path)
    write_json(artifact_path, dispatch)
    write_json(run_dir / "current-dispatch.json", dispatch)
    plan = write_execution_plan(run_dir, read_all_task_states(run_dir))
    return {
        "status": "pass",
        "decision": decision,
        "auto_event": auto_event,
        "dispatch_path": str(artifact_path),
        "dispatch": dispatch,
        "execution_plan": plan,
    }


def batch_dispatch_artifact_path(run_dir: Path) -> Path:
    return run_dir / "dispatch" / "agent-dispatch-batch.json"


def subagent_prompt_for_dispatch(dispatch: dict[str, Any]) -> str:
    route = dispatch["route"]
    task = dispatch["task"]
    lines = [
        f"You are the {route['role']} subagent for Lodestar task {task['task_id']}.",
        "",
        "You are not alone in the codebase. Other agents may work in parallel worktrees; do not revert their work.",
        f"Skill: {route['skill']}",
        f"Current state: {route['current_state']}",
        f"Branch: {task['branch']}",
        f"Worktree: {task['worktree']}",
        f"Write scope: {', '.join(task['write_scope'])}",
        f"Merge risk: {task['merge_risk']}",
        "",
        "Task:",
        task["title"],
        "",
        "Acceptance criteria:",
        *[f"- {item}" for item in task["acceptance_criteria"]],
        "",
        "Required output:",
        route["output_artifact"],
        "",
        "Expected Lodestar events:",
        *[f"- {event}" for event in route["expected_events"]],
    ]
    if route.get("review_stages"):
        lines.extend(["", "Review stages:", *[f"- {stage}" for stage in route["review_stages"]]])
    lines.extend(["", "Preserve locked product intent. Route product-impacting ambiguity to lodestar-course-correct."])
    return "\n".join(lines)


def batch_item_from_dispatch(dispatch: dict[str, Any]) -> dict[str, Any]:
    route = dispatch["route"]
    task = dispatch["task"]
    item = {
        "dispatch_id": dispatch["dispatch_id"],
        "task_id": task["task_id"],
        "title": task["title"],
        "role": route["role"],
        "skill": route["skill"],
        "current_state": route["current_state"],
        "worktree": task["worktree"],
        "branch": task["branch"],
        "parallel_group": task["parallel_group"],
        "write_scope": task["write_scope"],
        "merge_risk": task["merge_risk"],
        "expected_events": route["expected_events"],
        "output_artifact": route["output_artifact"],
        "prompt": subagent_prompt_for_dispatch(dispatch),
    }
    if route.get("review_stages"):
        item["review_stages"] = route["review_stages"]
    return item


def build_agent_dispatch_batch(
    run_dir: Path,
    task_states: list[dict[str, Any]],
    mode: str,
    spec_path: str,
    task_graph_path: str,
    items: list[dict[str, Any]],
    blocked_ready: list[dict[str, Any]],
) -> dict[str, Any]:
    run_id = task_states[0]["run_id"]
    spec_id = task_states[0]["spec_id"]
    batch = {
        "dispatch_batch_id": f"{run_id}-batch-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "created_at": utc_now(),
        "run_id": run_id,
        "spec_id": spec_id,
        "status": "ready" if items else ("complete" if all(task["state"] == "TASK_DONE" for task in task_states) else "blocked"),
        "mode": mode,
        "items": items,
        "blocked_ready": blocked_ready,
        "input_artifacts": {
            "locked_spec": spec_path,
            "task_graph": task_graph_path,
            "execution_plan": str(run_dir / "execution-plan.json"),
        },
        "upstream_source": {
            "repo": "superpowers",
            "paths": [
                "third_party/upstream/superpowers/skills/executing-plans",
                "third_party/upstream/superpowers/skills/subagent-driven-development",
                "third_party/upstream/superpowers/skills/test-driven-development",
                "third_party/upstream/superpowers/skills/requesting-code-review",
                "third_party/upstream/superpowers/skills/receiving-code-review",
                "third_party/upstream/superpowers/skills/using-git-worktrees",
                "third_party/upstream/superpowers/skills/verification-before-completion",
            ],
        },
        "execution_policy": {
            "spec_complete_means_sdd_ready": True,
            "dispatch_after_task_split": True,
            "max_parallel": True,
            "dependency_respecting": True,
            "worktree_isolation": True,
            "tdd_required": True,
            "builder_required": True,
            "reviewer_read_only": True,
            "merge_required": True,
            "user_owns_product_intent": True,
            "ce_forbidden_routes": sorted(CE_FORBIDDEN_ROUTES),
            "ce_return_routes": sorted(CE_RETURN_ROUTES),
        },
        "metrics": {
            "dispatchable": len(items),
            "ready_started": sum(1 for item in items if item["current_state"] == "IMPLEMENTING"),
            "active_dispatched": sum(1 for item in items if item["current_state"] != "IMPLEMENTING"),
            "blocked_ready": len(blocked_ready),
            "total_tasks": len(task_states),
        },
    }
    fail_if_errors(validate_agent_dispatch_batch_obj(batch))
    return batch


def dispatch_execution_batch(
    run_dir: Path,
    mode: str,
    spec_path: str,
    task_graph_path: str,
    out_path: Path | None = None,
) -> dict[str, Any]:
    if mode not in EXECUTION_DISPATCH_MODES:
        raise LodestarError(f"Unknown execution dispatch mode: {mode}")
    task_states = read_all_task_states(run_dir)
    by_id = states_by_task_id(task_states)
    updated_states: dict[str, dict[str, Any]] = {}
    blocked_ready: list[dict[str, Any]] = []
    dispatches: list[dict[str, Any]] = []

    for state in sorted(task_states, key=lambda item: item["task_id"]):
        current = state["state"]
        if current == "TASK_READY":
            pending = pending_dependencies(state, task_states)
            if pending:
                blocked_ready.append({"task_id": state["task_id"], "pending_dependencies": pending})
                continue
            artifact_path = dispatch_artifact_path(run_dir, state["task_id"])
            state = apply_task_event(
                state,
                "implementation-started",
                "max parallel execution driver dispatched dependency-unblocked task",
                str(artifact_path),
            )
            write_task_state(run_dir, state)
            updated_states[state["task_id"]] = state
        elif current not in DISPATCHABLE_ACTIVE_STATES:
            continue
        if state["state"] in EXECUTION_ROUTE_BY_STATE:
            dispatch = build_agent_dispatch(run_dir, state, mode, spec_path, task_graph_path)
            write_json(dispatch_artifact_path(run_dir, state["task_id"]), dispatch)
            dispatches.append(dispatch)
        by_id[state["task_id"]] = state

    refreshed_states = read_all_task_states(run_dir)
    items = [batch_item_from_dispatch(dispatch) for dispatch in dispatches]
    batch = build_agent_dispatch_batch(run_dir, refreshed_states, mode, spec_path, task_graph_path, items, blocked_ready)
    artifact_path = out_path or batch_dispatch_artifact_path(run_dir)
    write_json(artifact_path, batch)
    write_json(run_dir / "current-dispatch-batch.json", batch)
    plan = write_execution_plan(run_dir, refreshed_states)
    return {
        "status": batch["status"],
        "dispatch_batch_path": str(artifact_path),
        "dispatch_count": len(items),
        "blocked_ready": blocked_ready,
        "batch": batch,
        "execution_plan": plan,
    }
