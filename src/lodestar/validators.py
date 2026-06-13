"""Artifact validators (validate_* functions) for every Lodestar contract."""
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

from .core import *  # noqa: F401,F403


def validate_locked_spec_obj(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "id",
        "title",
        "status",
        "intent",
        "product_shape",
        "goals",
        "non_goals",
        "success_criteria",
        "acceptance_scenarios",
        "decisions",
        "decision_policy",
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

    product_shape = spec.get("product_shape")
    require(errors, isinstance(product_shape, dict), "product_shape must be an object")
    if isinstance(product_shape, dict):
        for field in ("primary_user", "first_screen", "core_flow", "approval_source"):
            require(errors, non_empty_string(product_shape.get(field)), f"product_shape.{field} must be non-empty")
        require(
            errors,
            non_empty_string_list(product_shape.get("ux_principles")),
            "product_shape.ux_principles must be a non-empty string list",
        )
        require(errors, product_shape.get("approved_preview") is True, "UX approval is required before product lock")

    require(errors, non_empty_string_list(spec.get("goals")), "locked spec goals must be a non-empty string list")
    require(errors, non_empty_string_list(spec.get("non_goals")), "locked spec non_goals must be a non-empty string list")

    success_criteria = spec.get("success_criteria")
    require(errors, isinstance(success_criteria, list) and bool(success_criteria), "success_criteria must be non-empty")
    seen_success: set[str] = set()
    if isinstance(success_criteria, list):
        for index, criterion in enumerate(success_criteria):
            prefix = f"success_criteria[{index}]"
            require(errors, isinstance(criterion, dict), f"{prefix} must be an object")
            if not isinstance(criterion, dict):
                continue
            cid = criterion.get("id")
            require(errors, non_empty_string(cid), f"{prefix}.id must be non-empty")
            require(errors, cid not in seen_success, f"{prefix}.id is duplicated: {cid}")
            if non_empty_string(cid):
                seen_success.add(cid)
            require(errors, non_empty_string(criterion.get("statement")), f"{prefix}.statement must be non-empty")
            require(errors, criterion.get("testable") is True, f"{prefix}.testable must be true")

    scenarios = spec.get("acceptance_scenarios")
    require(errors, isinstance(scenarios, list) and bool(scenarios), "acceptance_scenarios must be non-empty")
    seen_scenarios: set[str] = set()
    if isinstance(scenarios, list):
        for index, scenario in enumerate(scenarios):
            prefix = f"acceptance_scenarios[{index}]"
            require(errors, isinstance(scenario, dict), f"{prefix} must be an object")
            if not isinstance(scenario, dict):
                continue
            sid = scenario.get("id")
            require(errors, non_empty_string(sid), f"{prefix}.id must be non-empty")
            require(errors, sid not in seen_scenarios, f"{prefix}.id is duplicated: {sid}")
            if non_empty_string(sid):
                seen_scenarios.add(sid)
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

    decision_policy = spec.get("decision_policy")
    require(errors, isinstance(decision_policy, list) and bool(decision_policy), "decision_policy must be non-empty")
    seen_classes: set[str] = set()
    if isinstance(decision_policy, list):
        for index, policy in enumerate(decision_policy):
            prefix = f"decision_policy[{index}]"
            require(errors, isinstance(policy, dict), f"{prefix} must be an object")
            if not isinstance(policy, dict):
                continue
            decision_class = policy.get("class")
            require(errors, decision_class in DECISION_CLASSES, f"{prefix}.class must be a known decision class")
            if isinstance(decision_class, str):
                seen_classes.add(decision_class)
            require(errors, policy.get("owner") in DECISION_OWNERS, f"{prefix}.owner must be harness, user, or advisor")
            require(errors, non_empty_string(policy.get("default_action")), f"{prefix}.default_action must be non-empty")
        missing_classes = sorted(DECISION_CLASSES - seen_classes)
        require(errors, not missing_classes, f"decision_policy missing classes: {', '.join(missing_classes)}")

    gate_evidence = spec.get("gate_evidence")
    require(errors, isinstance(gate_evidence, dict), "gate_evidence must be an object")
    if isinstance(gate_evidence, dict):
        for gate in PRODUCT_LOCK_GATES:
            require(errors, gate_evidence.get(gate) == "pass", f"gate_evidence.{gate} must be 'pass'")
    return errors


def spec_cover_ids(spec: dict[str, Any]) -> set[str]:
    success_ids = {item["id"] for item in spec.get("success_criteria", []) if isinstance(item, dict) and "id" in item}
    scenario_ids = {item["id"] for item in spec.get("acceptance_scenarios", []) if isinstance(item, dict) and "id" in item}
    return success_ids | scenario_ids


def validate_task_graph_obj(task_graph: dict[str, Any], spec: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    for key in ("spec_id", "status", "tasks"):
        require(errors, key in task_graph, f"task graph missing required field: {key}")
    require(errors, task_graph.get("status") == "ready", "task graph status must be 'ready'")
    if spec is not None:
        require(errors, task_graph.get("spec_id") == spec.get("id"), "task graph spec_id must match locked spec id")

    tasks = task_graph.get("tasks")
    require(errors, isinstance(tasks, list) and bool(tasks), "tasks must be a non-empty list")
    if not isinstance(tasks, list):
        return errors

    task_ids: set[str] = set()
    for index, task in enumerate(tasks):
        prefix = f"tasks[{index}]"
        require(errors, isinstance(task, dict), f"{prefix} must be an object")
        if not isinstance(task, dict):
            continue
        tid = task.get("id")
        require(errors, non_empty_string(tid), f"{prefix}.id must be non-empty")
        require(errors, tid not in task_ids, f"{prefix}.id is duplicated: {tid}")
        if non_empty_string(tid):
            task_ids.add(tid)
        for field in ("title", "branch", "role"):
            require(errors, non_empty_string(task.get(field)), f"{prefix}.{field} must be non-empty")
        require(errors, task.get("role") in {"implementer", "builder", "reviewer", "fixer"}, f"{prefix}.role is invalid")
        require(errors, non_empty_string_list(task.get("acceptance_criteria")), f"{prefix}.acceptance_criteria must be a non-empty string list")
        require(errors, non_empty_string_list(task.get("covers")), f"{prefix}.covers must be a non-empty string list")
        require(errors, isinstance(task.get("dependencies"), list), f"{prefix}.dependencies must be a list")
        if "parallel_group" in task:
            require(errors, non_empty_string(task.get("parallel_group")), f"{prefix}.parallel_group must be non-empty when provided")
        if "write_scope" in task:
            require(errors, non_empty_string_list(task.get("write_scope")), f"{prefix}.write_scope must be a non-empty string list when provided")
        if "merge_risk" in task:
            require(errors, task.get("merge_risk") in MERGE_RISKS, f"{prefix}.merge_risk must be low, medium, or high when provided")

    for index, task in enumerate(tasks):
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
        for task in tasks:
            if isinstance(task, dict) and isinstance(task.get("covers"), list):
                actual_covers.update(item for item in task["covers"] if isinstance(item, str))
        missing = sorted(required_covers - actual_covers)
        unknown = sorted(actual_covers - required_covers)
        require(errors, not missing, f"task split gate missing coverage for: {', '.join(missing)}")
        require(errors, not unknown, f"task split gate has unknown cover ids: {', '.join(unknown)}")
    return errors


def task_parallel_group(task: dict[str, Any]) -> str:
    value = task.get("parallel_group")
    return value if non_empty_string(value) else "default"


def task_write_scope(task: dict[str, Any]) -> list[str]:
    value = task.get("write_scope")
    if non_empty_string_list(value):
        return list(value)
    branch = task.get("branch")
    return [branch_path_safe(branch) if non_empty_string(branch) else task.get("id", "task")]


def task_merge_risk(task: dict[str, Any]) -> str:
    value = task.get("merge_risk")
    return value if value in MERGE_RISKS else "medium"


def task_graph_parallel_warnings(task_graph: dict[str, Any]) -> list[str]:
    warnings = []
    tasks = task_graph.get("tasks", [])
    if not isinstance(tasks, list):
        return warnings
    missing_metadata = [
        task.get("id", f"task-{index}")
        for index, task in enumerate(tasks)
        if isinstance(task, dict)
        and ("parallel_group" not in task or "write_scope" not in task or "merge_risk" not in task)
    ]
    if missing_metadata:
        warnings.append("parallel metadata missing for: " + ", ".join(str(item) for item in missing_metadata))
    roots = [task for task in tasks if isinstance(task, dict) and not task.get("dependencies")]
    if len(tasks) > 3 and len(roots) <= 1:
        warnings.append("only one dependency-free root task; max-parallel execution may be bottlenecked")
    broad_roots = [
        task.get("id", "unknown")
        for task in roots
        if isinstance(task, dict)
        and (
            len(task.get("covers", [])) >= 4
            or any(scope in {"*", "Sources", "src", "app"} for scope in task_write_scope(task))
        )
    ]
    if broad_roots:
        warnings.append("broad foundation/root task may need split: " + ", ".join(str(item) for item in broad_roots))
    return warnings


def task_allowed_events(state: str) -> list[str]:
    return sorted(event for current, event in TASK_TRANSITIONS if current == state)


def task_status_for_state(state: str) -> str:
    if state == "TASK_READY":
        return "ready"
    if state == "TASK_DONE":
        return "done"
    if state == "TASK_BLOCKED":
        return "blocked"
    return "in-progress"


def validate_task_state_obj(task_state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "run_id",
        "spec_id",
        "task_id",
        "title",
        "branch",
        "role",
        "state",
        "status",
        "worktree",
        "covers",
        "dependencies",
        "acceptance_criteria",
        "attempts",
        "gates",
        "next_allowed_events",
        "history",
    ]
    for key in required:
        require(errors, key in task_state, f"task state missing required field: {key}")
    for key in ("run_id", "spec_id", "task_id", "title", "branch", "role", "worktree"):
        require(errors, non_empty_string(task_state.get(key)), f"task state {key} must be non-empty")
    state = task_state.get("state")
    require(errors, state in TASK_STATES, "task state is invalid")
    require(errors, task_state.get("status") in TASK_STATUSES, "task status is invalid")
    if isinstance(state, str) and state in TASK_STATES:
        require(errors, task_state.get("status") == task_status_for_state(state), "task status must match task state")
        require(errors, task_state.get("next_allowed_events") == task_allowed_events(state), "next_allowed_events must match task state")
    require(errors, task_state.get("role") in {"implementer", "builder", "reviewer", "fixer"}, "task role is invalid")
    require(errors, non_empty_string_list(task_state.get("covers")), "task state covers must be a non-empty string list")
    require(errors, non_empty_string_list(task_state.get("acceptance_criteria")), "task state acceptance_criteria must be a non-empty string list")
    require(errors, isinstance(task_state.get("dependencies"), list), "task state dependencies must be a list")
    if "parallel_group" in task_state:
        require(errors, non_empty_string(task_state.get("parallel_group")), "task state parallel_group must be non-empty")
    if "write_scope" in task_state:
        require(errors, non_empty_string_list(task_state.get("write_scope")), "task state write_scope must be a non-empty string list")
    if "merge_risk" in task_state:
        require(errors, task_state.get("merge_risk") in MERGE_RISKS, "task state merge_risk must be low, medium, or high")
    attempts = task_state.get("attempts")
    require(errors, isinstance(attempts, dict), "task state attempts must be an object")
    if isinstance(attempts, dict):
        for key in ("implementation_attempts", "build_attempts", "review_attempts", "fix_attempts", "ce_cycles"):
            require(errors, isinstance(attempts.get(key), int) and attempts.get(key) >= 0, f"attempts.{key} must be a non-negative integer")
    gates = task_state.get("gates")
    require(errors, isinstance(gates, dict), "task state gates must be an object")
    if isinstance(gates, dict):
        for key in TASK_GATE_DEFAULTS:
            value = gates.get(key)
            if value is None and key == "merge":
                value = "pending"
            require(errors, value in {"pending", "pass", "fail", "not-needed"}, f"gates.{key} is invalid")
    require(errors, isinstance(task_state.get("history"), list), "task state history must be a list")
    return errors


def validate_execution_plan_obj(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ["run_id", "spec_id", "status", "upstream_source", "task_count", "tasks", "metrics"]
    for key in required:
        require(errors, key in plan, f"execution plan missing required field: {key}")
    require(errors, non_empty_string(plan.get("run_id")), "execution plan run_id must be non-empty")
    require(errors, non_empty_string(plan.get("spec_id")), "execution plan spec_id must be non-empty")
    require(errors, plan.get("status") in TASK_STATUSES, "execution plan status is invalid")

    upstream_source = plan.get("upstream_source")
    require(errors, isinstance(upstream_source, dict), "execution plan upstream_source must be an object")
    if isinstance(upstream_source, dict):
        require(errors, upstream_source.get("repo") == "superpowers", "execution plan upstream_source.repo must be superpowers")
        require(errors, non_empty_string(upstream_source.get("adapter")), "execution plan upstream_source.adapter must be non-empty")
        require(errors, non_empty_string_list(upstream_source.get("paths")), "execution plan upstream_source.paths must be a non-empty string list")

    tasks = plan.get("tasks")
    require(errors, isinstance(tasks, list) and bool(tasks), "execution plan tasks must be a non-empty list")
    if isinstance(tasks, list):
        require(errors, plan.get("task_count") == len(tasks), "execution plan task_count must match tasks length")
        task_ids: set[str] = set()
        for index, task in enumerate(tasks):
            prefix = f"tasks[{index}]"
            require(errors, isinstance(task, dict), f"{prefix} must be an object")
            if not isinstance(task, dict):
                continue
            tid = task.get("task_id")
            require(errors, non_empty_string(tid), f"{prefix}.task_id must be non-empty")
            require(errors, tid not in task_ids, f"{prefix}.task_id duplicated: {tid}")
            if non_empty_string(tid):
                task_ids.add(tid)
            for field in ("title", "branch", "role", "state", "status", "worktree", "state_path"):
                require(errors, non_empty_string(task.get(field)), f"{prefix}.{field} must be non-empty")
            require(errors, task.get("state") in TASK_STATES, f"{prefix}.state is invalid")
            require(errors, task.get("status") in TASK_STATUSES, f"{prefix}.status is invalid")
            require(errors, isinstance(task.get("dependencies"), list), f"{prefix}.dependencies must be a list")
            require(errors, isinstance(task.get("next_allowed_events"), list), f"{prefix}.next_allowed_events must be a list")
            attempts = task.get("attempts")
            require(errors, isinstance(attempts, dict), f"{prefix}.attempts must be an object")
            if isinstance(attempts, dict):
                for key in ("implementation_attempts", "build_attempts", "review_attempts", "fix_attempts", "ce_cycles"):
                    require(errors, isinstance(attempts.get(key), int) and attempts.get(key) >= 0, f"{prefix}.attempts.{key} must be a non-negative integer")
            gates = task.get("gates")
            require(errors, isinstance(gates, dict), f"{prefix}.gates must be an object")
            if isinstance(gates, dict):
                for key in TASK_GATE_DEFAULTS:
                    value = gates.get(key)
                    if value is None and key == "merge":
                        value = "pending"
                    require(errors, value in {"pending", "pass", "fail", "not-needed"}, f"{prefix}.gates.{key} is invalid")
        for index, task in enumerate(tasks):
            if not isinstance(task, dict):
                continue
            for dep in task.get("dependencies", []):
                require(errors, dep in task_ids, f"tasks[{index}].dependencies references missing task: {dep}")

    metrics = plan.get("metrics")
    require(errors, isinstance(metrics, dict), "execution plan metrics must be an object")
    if isinstance(metrics, dict):
        for key in ("ready", "in_progress", "done", "blocked", "total"):
            require(errors, isinstance(metrics.get(key), int) and metrics.get(key) >= 0, f"metrics.{key} must be a non-negative integer")
        if isinstance(tasks, list):
            require(errors, metrics.get("total") == len(tasks), "metrics.total must match tasks length")
    return errors


def validate_agent_dispatch_obj(dispatch: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "dispatch_id",
        "created_at",
        "run_id",
        "spec_id",
        "status",
        "mode",
        "route",
        "task",
        "input_artifacts",
        "upstream_source",
        "execution_policy",
        "expected_events",
    ]
    for key in required:
        require(errors, key in dispatch, f"agent dispatch missing required field: {key}")
    for key in ("dispatch_id", "created_at", "run_id", "spec_id"):
        require(errors, non_empty_string(dispatch.get(key)), f"agent dispatch {key} must be non-empty")
    require(errors, dispatch.get("status") in {"ready", "blocked", "complete"}, "agent dispatch status is invalid")
    require(errors, dispatch.get("mode") in EXECUTION_DISPATCH_MODES, "agent dispatch mode is invalid")

    route = dispatch.get("route")
    require(errors, isinstance(route, dict), "agent dispatch route must be an object")
    if isinstance(route, dict):
        for key in ("skill", "role", "current_state", "next_step", "output_artifact"):
            require(errors, non_empty_string(route.get(key)), f"agent dispatch route.{key} must be non-empty")
        state = route.get("current_state")
        require(errors, state in TASK_STATES, "agent dispatch route.current_state is invalid")
        if state in EXECUTION_ROUTE_BY_STATE:
            expected = EXECUTION_ROUTE_BY_STATE[state]
            require(errors, route.get("skill") == expected["skill"], "agent dispatch route.skill does not match task state")
            require(errors, route.get("role") == expected["role"], "agent dispatch route.role does not match task state")
            require(errors, route.get("mutates_code") is expected["mutates_code"], "agent dispatch route.mutates_code does not match task state")
        if route.get("role") == "reviewer":
            require(errors, route.get("mutates_code") is False, "reviewer dispatch must be read-only")
            require(errors, route.get("review_stages") == list(REVIEW_STAGES), "reviewer dispatch must require spec then code quality review stages")

    task = dispatch.get("task")
    require(errors, isinstance(task, dict), "agent dispatch task must be an object")
    if isinstance(task, dict):
        for key in ("task_id", "title", "branch", "worktree"):
            require(errors, non_empty_string(task.get(key)), f"agent dispatch task.{key} must be non-empty")
        require(errors, non_empty_string_list(task.get("covers")), "agent dispatch task.covers must be a non-empty string list")
        require(
            errors,
            non_empty_string_list(task.get("acceptance_criteria")),
            "agent dispatch task.acceptance_criteria must be a non-empty string list",
        )
        require(errors, isinstance(task.get("dependencies"), list), "agent dispatch task.dependencies must be a list")
        require(errors, non_empty_string(task.get("parallel_group")), "agent dispatch task.parallel_group must be non-empty")
        require(errors, non_empty_string_list(task.get("write_scope")), "agent dispatch task.write_scope must be a non-empty string list")
        require(errors, task.get("merge_risk") in MERGE_RISKS, "agent dispatch task.merge_risk must be low, medium, or high")
        require(errors, isinstance(task.get("gates"), dict), "agent dispatch task.gates must be an object")
        require(errors, isinstance(task.get("attempts"), dict), "agent dispatch task.attempts must be an object")

    input_artifacts = dispatch.get("input_artifacts")
    require(errors, isinstance(input_artifacts, dict), "agent dispatch input_artifacts must be an object")
    if isinstance(input_artifacts, dict):
        for key in ("locked_spec", "task_graph", "execution_plan", "task_state"):
            require(errors, non_empty_string(input_artifacts.get(key)), f"agent dispatch input_artifacts.{key} must be non-empty")

    upstream_source = dispatch.get("upstream_source")
    require(errors, isinstance(upstream_source, dict), "agent dispatch upstream_source must be an object")
    if isinstance(upstream_source, dict):
        require(errors, upstream_source.get("repo") == "superpowers", "agent dispatch upstream_source.repo must be superpowers")
        require(errors, non_empty_string_list(upstream_source.get("paths")), "agent dispatch upstream_source.paths must be a non-empty string list")

    policy = dispatch.get("execution_policy")
    require(errors, isinstance(policy, dict), "agent dispatch execution_policy must be an object")
    if isinstance(policy, dict):
        for key in (
            "spec_complete_means_sdd_ready",
            "dispatch_after_task_split",
            "tdd_required",
            "builder_required",
            "reviewer_read_only",
            "user_owns_product_intent",
        ):
            require(errors, policy.get(key) is True, f"agent dispatch execution_policy.{key} must be true")
        require(
            errors,
            policy.get("ce_forbidden_routes") == sorted(CE_FORBIDDEN_ROUTES),
            "agent dispatch execution_policy.ce_forbidden_routes must match Lodestar CE constraints",
        )

    expected_events = dispatch.get("expected_events")
    require(errors, non_empty_string_list(expected_events), "agent dispatch expected_events must be a non-empty string list")
    if isinstance(route, dict) and route.get("current_state") in EXECUTION_ROUTE_BY_STATE and isinstance(expected_events, list):
        require(
            errors,
            expected_events == EXECUTION_ROUTE_BY_STATE[route["current_state"]]["expected_events"],
            "agent dispatch expected_events do not match task state",
        )
    return errors


def validate_agent_dispatch_batch_obj(batch: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "dispatch_batch_id",
        "created_at",
        "run_id",
        "spec_id",
        "status",
        "mode",
        "items",
        "input_artifacts",
        "upstream_source",
        "execution_policy",
        "metrics",
    ]
    for key in required:
        require(errors, key in batch, f"agent dispatch batch missing required field: {key}")
    for key in ("dispatch_batch_id", "created_at", "run_id", "spec_id"):
        require(errors, non_empty_string(batch.get(key)), f"agent dispatch batch {key} must be non-empty")
    require(errors, batch.get("status") in {"ready", "blocked", "complete"}, "agent dispatch batch status is invalid")
    require(errors, batch.get("mode") in EXECUTION_DISPATCH_MODES, "agent dispatch batch mode is invalid")

    input_artifacts = batch.get("input_artifacts")
    require(errors, isinstance(input_artifacts, dict), "agent dispatch batch input_artifacts must be an object")
    if isinstance(input_artifacts, dict):
        for key in ("locked_spec", "task_graph", "execution_plan"):
            require(errors, non_empty_string(input_artifacts.get(key)), f"agent dispatch batch input_artifacts.{key} must be non-empty")

    upstream_source = batch.get("upstream_source")
    require(errors, isinstance(upstream_source, dict), "agent dispatch batch upstream_source must be an object")
    if isinstance(upstream_source, dict):
        require(errors, upstream_source.get("repo") == "superpowers", "agent dispatch batch upstream_source.repo must be superpowers")
        require(errors, non_empty_string_list(upstream_source.get("paths")), "agent dispatch batch upstream_source.paths must be a non-empty string list")

    policy = batch.get("execution_policy")
    require(errors, isinstance(policy, dict), "agent dispatch batch execution_policy must be an object")
    if isinstance(policy, dict):
        for key in (
            "spec_complete_means_sdd_ready",
            "dispatch_after_task_split",
            "max_parallel",
            "dependency_respecting",
            "worktree_isolation",
            "tdd_required",
            "builder_required",
            "reviewer_read_only",
            "merge_required",
            "user_owns_product_intent",
        ):
            require(errors, policy.get(key) is True, f"agent dispatch batch execution_policy.{key} must be true")

    items = batch.get("items")
    require(errors, isinstance(items, list), "agent dispatch batch items must be a list")
    if isinstance(items, list):
        seen: set[str] = set()
        for index, item in enumerate(items):
            prefix = f"items[{index}]"
            require(errors, isinstance(item, dict), f"{prefix} must be an object")
            if not isinstance(item, dict):
                continue
            for key in (
                "dispatch_id",
                "task_id",
                "title",
                "role",
                "skill",
                "current_state",
                "worktree",
                "branch",
                "parallel_group",
                "merge_risk",
                "output_artifact",
                "prompt",
            ):
                require(errors, non_empty_string(item.get(key)), f"{prefix}.{key} must be non-empty")
            dispatch_id = item.get("dispatch_id")
            require(errors, dispatch_id not in seen, f"{prefix}.dispatch_id duplicated: {dispatch_id}")
            if non_empty_string(dispatch_id):
                seen.add(dispatch_id)
            state = item.get("current_state")
            require(errors, state in EXECUTION_ROUTE_BY_STATE, f"{prefix}.current_state must be dispatchable")
            if state in EXECUTION_ROUTE_BY_STATE:
                expected = EXECUTION_ROUTE_BY_STATE[state]
                require(errors, item.get("role") == expected["role"], f"{prefix}.role does not match state")
                require(errors, item.get("skill") == expected["skill"], f"{prefix}.skill does not match state")
                require(errors, item.get("expected_events") == expected["expected_events"], f"{prefix}.expected_events do not match state")
                if item.get("role") == "reviewer":
                    require(errors, item.get("review_stages") == list(REVIEW_STAGES), f"{prefix}.review_stages must require two-stage review")
            require(errors, non_empty_string_list(item.get("write_scope")), f"{prefix}.write_scope must be a non-empty string list")
            require(errors, item.get("merge_risk") in MERGE_RISKS, f"{prefix}.merge_risk must be low, medium, or high")

    metrics = batch.get("metrics")
    require(errors, isinstance(metrics, dict), "agent dispatch batch metrics must be an object")
    if isinstance(metrics, dict):
        for key in ("dispatchable", "ready_started", "active_dispatched", "blocked_ready", "total_tasks"):
            require(errors, isinstance(metrics.get(key), int) and metrics.get(key) >= 0, f"metrics.{key} must be a non-negative integer")
    return errors


def validate_build_evidence_obj(evidence: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("task_id", "status", "commands", "summary"):
        require(errors, key in evidence, f"build evidence missing required field: {key}")
    require(errors, evidence.get("status") in {"pass", "fail"}, "build evidence status must be pass or fail")
    require(errors, isinstance(evidence.get("commands"), list) and bool(evidence.get("commands")), "commands must be non-empty")
    return errors


def validate_review_report_obj(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("task_id", "status", "reviewer_read_only", "code_edits_made", "findings", "review_stages"):
        require(errors, key in report, f"review report missing required field: {key}")
    require(errors, report.get("status") in {"approved", "rejected"}, "review status must be approved or rejected")
    require(errors, report.get("reviewer_read_only") is True, "reviewer must be read-only")
    require(errors, report.get("code_edits_made") is False, "reviewer must not edit code")
    review_stages = report.get("review_stages")
    require(errors, isinstance(review_stages, list) and len(review_stages) == len(REVIEW_STAGES), "review_stages must include spec and code quality review")
    if isinstance(review_stages, list):
        stage_names = [stage.get("stage") for stage in review_stages if isinstance(stage, dict)]
        require(errors, stage_names == list(REVIEW_STAGES), "review_stages must run spec-compliance-review before code-quality-review")
        for index, stage in enumerate(review_stages):
            prefix = f"review_stages[{index}]"
            require(errors, isinstance(stage, dict), f"{prefix} must be an object")
            if not isinstance(stage, dict):
                continue
            require(errors, stage.get("status") in {"approved", "rejected"}, f"{prefix}.status must be approved or rejected")
            require(errors, non_empty_string(stage.get("summary")), f"{prefix}.summary must be non-empty")
        if report.get("status") == "approved":
            require(errors, all(isinstance(stage, dict) and stage.get("status") == "approved" for stage in review_stages), "approved review requires both review stages to approve")
    require(errors, isinstance(report.get("findings"), list), "findings must be a list")
    findings = report.get("findings")
    if isinstance(findings, list):
        for index, finding in enumerate(findings):
            prefix = f"findings[{index}]"
            require(errors, isinstance(finding, dict), f"{prefix} must be an object")
            if not isinstance(finding, dict):
                continue
            require(errors, finding.get("severity") in {"P0", "P1", "P2", "P3"}, f"{prefix}.severity must be P0-P3")
            require(errors, non_empty_string(finding.get("summary")), f"{prefix}.summary must be non-empty")
            require(
                errors,
                finding.get("owner") in {"fixer", "debrief", "amend-advisor", "human"},
                f"{prefix}.owner must be fixer, debrief, amend-advisor, or human",
            )
            require(errors, isinstance(finding.get("requires_verification"), bool), f"{prefix}.requires_verification must be boolean")
    return errors


def validate_amendment_request_obj(request: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("id", "class", "requires_user_approval", "auto_approved", "options"):
        require(errors, key in request, f"amendment request missing required field: {key}")
    require(errors, request.get("requires_user_approval") is True, "amendment advisor must require user approval")
    require(errors, request.get("auto_approved") is False, "amendment advisor cannot auto-approve product intent")
    require(errors, isinstance(request.get("options"), list) and bool(request.get("options")), "options must be non-empty")
    return errors


def validate_final_handoff_obj(handoff: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("id", "status", "summary", "gates", "evidence", "artifacts", "next_action"):
        require(errors, key in handoff, f"final handoff missing required field: {key}")
    require(errors, handoff.get("status") == "pass", "final handoff status must be pass")
    gates = handoff.get("gates")
    require(errors, isinstance(gates, dict), "final handoff gates must be an object")
    if isinstance(gates, dict):
        for gate in PROOF_BUNDLE_GATES:
            require(errors, gates.get(gate) == "pass", f"final handoff gate {gate} must be pass")
    require(errors, isinstance(handoff.get("evidence"), list) and bool(handoff.get("evidence")), "handoff evidence must be non-empty")
    artifacts = handoff.get("artifacts")
    require(errors, isinstance(artifacts, dict), "final handoff artifacts must be an object")
    if isinstance(artifacts, dict):
        for key in ("proof_bundle", "quality_report"):
            require(errors, non_empty_string(artifacts.get(key)), f"final handoff artifacts.{key} must be non-empty")
    return errors


def validate_proof_bundle_obj(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("run_id", "status", "gates", "artifacts", "summary"):
        require(errors, key in bundle, f"proof bundle missing required field: {key}")
    require(errors, non_empty_string(bundle.get("run_id")), "proof bundle run_id must be non-empty")
    require(errors, bundle.get("status") in {"pass", "fail", "in-progress"}, "proof bundle status is invalid")
    gates = bundle.get("gates")
    require(errors, isinstance(gates, dict), "proof bundle gates must be an object")
    if isinstance(gates, dict):
        for gate in PROOF_BUNDLE_GATES:
            require(errors, gate in gates, f"proof bundle missing gate: {gate}")
            require(errors, gates.get(gate) in {"pass", "fail", "pending"}, f"proof bundle gate {gate} is invalid")
        if bundle.get("status") == "pass":
            for gate in PROOF_BUNDLE_GATES:
                require(errors, gates.get(gate) == "pass", f"passing proof bundle gate {gate} must be pass")
    artifacts = bundle.get("artifacts")
    require(errors, isinstance(artifacts, dict), "proof bundle artifacts must be an object")
    if isinstance(artifacts, dict) and bundle.get("status") == "pass":
        for gate, artifact_key in QUALITY_REQUIRED_PASS_ARTIFACTS.items():
            require(errors, non_empty_string(artifacts.get(artifact_key)), f"passing proof bundle missing artifact for {gate}: {artifact_key}")
    return errors


def validate_upstream_map_obj(upstream_map: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    require(errors, upstream_map.get("schema_version") == 1, "upstream map schema_version must be 1")
    require(errors, upstream_map.get("strategy") == "completeness-first", "upstream map strategy must be completeness-first")
    policy = upstream_map.get("policy")
    require(errors, isinstance(policy, dict), "upstream map policy must be an object")
    if isinstance(policy, dict):
        require(errors, policy.get("expose_upstream_skills_directly") is False, "upstream skills must not be exposed directly")
        require(errors, policy.get("adapter_required") is True, "upstream adapters are required")
        require(errors, policy.get("user_intent_owner") == "user", "user intent owner must be user")

    repos = upstream_map.get("repositories")
    require(errors, isinstance(repos, list) and bool(repos), "upstream map repositories must be non-empty")
    seen_ids: set[str] = set()
    if isinstance(repos, list):
        for index, repo in enumerate(repos):
            prefix = f"repositories[{index}]"
            require(errors, isinstance(repo, dict), f"{prefix} must be an object")
            if not isinstance(repo, dict):
                continue
            rid = repo.get("id")
            require(errors, non_empty_string(rid), f"{prefix}.id must be non-empty")
            require(errors, rid not in seen_ids, f"{prefix}.id duplicated: {rid}")
            if non_empty_string(rid):
                seen_ids.add(rid)
            for field in ("name", "url", "commit", "license", "notice", "vendored_root", "contract_summary"):
                require(errors, non_empty_string(repo.get(field)), f"{prefix}.{field} must be non-empty")
            require(errors, repo.get("license") == "MIT", f"{prefix}.license must be MIT")
            vendored_root = root / str(repo.get("vendored_root", ""))
            require(errors, vendored_root.exists(), f"{prefix}.vendored_root does not exist: {vendored_root}")
            require(errors, (vendored_root / "LICENSE").exists(), f"{prefix} missing vendored LICENSE")
            imported_roots = repo.get("imported_roots")
            require(errors, isinstance(imported_roots, list) and bool(imported_roots), f"{prefix}.imported_roots must be non-empty")
            if isinstance(imported_roots, list):
                for imported_index, imported in enumerate(imported_roots):
                    require(errors, non_empty_string(imported), f"{prefix}.imported_roots[{imported_index}] must be non-empty")
                    if non_empty_string(imported):
                        require(errors, (root / imported).exists(), f"{prefix}.imported_roots[{imported_index}] missing: {imported}")
            layers = repo.get("lodestar_layers")
            require(errors, isinstance(layers, list) and bool(layers), f"{prefix}.lodestar_layers must be non-empty")
            if isinstance(layers, list):
                for layer in layers:
                    require(errors, layer in UPSTREAM_LAYERS, f"{prefix}.lodestar_layers has unknown layer: {layer}")
            target_skills = repo.get("target_skills")
            require(errors, isinstance(target_skills, list) and bool(target_skills), f"{prefix}.target_skills must be non-empty")
            if isinstance(target_skills, list):
                for skill in target_skills:
                    require(errors, skill in SKILLS, f"{prefix}.target_skills has unknown skill: {skill}")
    missing_repo_ids = {"spec-kit", "superpowers", "compound-engineering-plugin", "gstack"} - seen_ids
    require(errors, not missing_repo_ids, f"upstream map missing repositories: {', '.join(sorted(missing_repo_ids))}")
    return errors


def validate_spec_gate_report_obj(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("spec_id", "status", "upstream_source", "categories", "findings", "metrics", "next_route"):
        require(errors, key in report, f"spec gate report missing required field: {key}")
    require(errors, non_empty_string(report.get("spec_id")), "spec gate report spec_id must be non-empty")
    require(errors, report.get("status") in {"pass", "fail"}, "spec gate report status must be pass or fail")
    require(errors, report.get("next_route") in SKILLS, "spec gate report next_route must be a Lodestar skill")

    upstream_source = report.get("upstream_source")
    require(errors, isinstance(upstream_source, dict), "upstream_source must be an object")
    if isinstance(upstream_source, dict):
        require(errors, upstream_source.get("repo") == "spec-kit", "upstream_source.repo must be spec-kit")
        require(errors, non_empty_string(upstream_source.get("adapter")), "upstream_source.adapter must be non-empty")
        require(errors, non_empty_string_list(upstream_source.get("paths")), "upstream_source.paths must be a non-empty string list")

    categories = report.get("categories")
    require(errors, isinstance(categories, dict), "categories must be an object")
    if isinstance(categories, dict):
        missing_categories = [category for category in SPEC_GATE_CATEGORIES if category not in categories]
        require(errors, not missing_categories, f"spec gate report missing categories: {', '.join(missing_categories)}")
        for category, category_report in categories.items():
            require(errors, category in SPEC_GATE_CATEGORIES, f"unknown spec gate category: {category}")
            require(errors, isinstance(category_report, dict), f"categories.{category} must be an object")
            if not isinstance(category_report, dict):
                continue
            require(errors, category_report.get("status") in SPEC_GATE_STATUSES, f"categories.{category}.status is invalid")
            require(errors, non_empty_string(category_report.get("summary")), f"categories.{category}.summary must be non-empty")

    findings = report.get("findings")
    require(errors, isinstance(findings, list), "findings must be a list")
    high_or_critical = False
    if isinstance(findings, list):
        seen_finding_ids: set[str] = set()
        for index, finding in enumerate(findings):
            prefix = f"findings[{index}]"
            require(errors, isinstance(finding, dict), f"{prefix} must be an object")
            if not isinstance(finding, dict):
                continue
            fid = finding.get("id")
            require(errors, non_empty_string(fid), f"{prefix}.id must be non-empty")
            require(errors, fid not in seen_finding_ids, f"{prefix}.id is duplicated: {fid}")
            if non_empty_string(fid):
                seen_finding_ids.add(fid)
            require(errors, finding.get("category") in SPEC_GATE_CATEGORIES, f"{prefix}.category is invalid")
            severity = finding.get("severity")
            require(errors, severity in SPEC_GATE_SEVERITIES, f"{prefix}.severity is invalid")
            if severity in {"critical", "high"}:
                high_or_critical = True
            for field in ("summary", "recommendation", "source"):
                require(errors, non_empty_string(finding.get(field)), f"{prefix}.{field} must be non-empty")

    metrics = report.get("metrics")
    require(errors, isinstance(metrics, dict), "metrics must be an object")
    if isinstance(metrics, dict):
        for key in (
            "total_findings",
            "critical_findings",
            "high_findings",
            "medium_findings",
            "low_findings",
            "category_pass_count",
            "category_fail_count",
            "category_not_applicable_count",
        ):
            require(errors, isinstance(metrics.get(key), int) and metrics.get(key) >= 0, f"metrics.{key} must be a non-negative integer")
        if isinstance(findings, list):
            require(errors, metrics.get("total_findings") == len(findings), "metrics.total_findings must match findings length")

    if report.get("status") == "pass":
        require(errors, not high_or_critical, "passing spec gate report cannot contain critical/high findings")
        require(errors, report.get("next_route") == "lodestar-stages", "passing spec gate report must route to lodestar-stages")
    if report.get("status") == "fail":
        require(errors, high_or_critical, "failing spec gate report must contain at least one critical/high finding")
        require(errors, report.get("next_route") != "lodestar-stages", "failing spec gate report cannot route to lodestar-stages")
    return errors


def validate_browser_evidence_obj(evidence: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("run_id", "status", "mode", "target", "captured_at", "upstream_source", "viewport", "page", "checks", "findings", "metrics", "artifacts"):
        require(errors, key in evidence, f"browser evidence missing required field: {key}")
    require(errors, non_empty_string(evidence.get("run_id")), "browser evidence run_id must be non-empty")
    require(errors, evidence.get("status") in {"pass", "fail"}, "browser evidence status must be pass or fail")
    require(errors, evidence.get("mode") in BROWSER_EVIDENCE_MODES, "browser evidence mode is invalid")
    require(errors, non_empty_string(evidence.get("captured_at")), "browser evidence captured_at must be non-empty")

    target = evidence.get("target")
    require(errors, isinstance(target, dict), "browser evidence target must be an object")
    if isinstance(target, dict):
        require(errors, non_empty_string(target.get("source")), "browser evidence target.source must be non-empty")
        require(errors, target.get("type") in {"url", "html", "snapshot", "manual"}, "browser evidence target.type is invalid")

    upstream_source = evidence.get("upstream_source")
    require(errors, isinstance(upstream_source, dict), "browser evidence upstream_source must be an object")
    if isinstance(upstream_source, dict):
        require(errors, upstream_source.get("repo") in {"gstack", "compound-engineering-plugin"}, "browser evidence upstream_source.repo is invalid")
        require(errors, non_empty_string(upstream_source.get("adapter")), "browser evidence upstream_source.adapter must be non-empty")
        require(errors, non_empty_string_list(upstream_source.get("paths")), "browser evidence upstream_source.paths must be non-empty")

    viewport = evidence.get("viewport")
    require(errors, isinstance(viewport, dict), "browser evidence viewport must be an object")
    if isinstance(viewport, dict):
        require(errors, non_empty_string(viewport.get("name")), "browser evidence viewport.name must be non-empty")
        for key in ("width", "height"):
            require(errors, isinstance(viewport.get(key), int) and viewport.get(key) > 0, f"browser evidence viewport.{key} must be positive integer")

    page = evidence.get("page")
    require(errors, isinstance(page, dict), "browser evidence page must be an object")
    if isinstance(page, dict):
        require(errors, isinstance(page.get("title"), str), "browser evidence page.title must be a string")
        require(errors, isinstance(page.get("text_length"), int) and page.get("text_length") >= 0, "browser evidence page.text_length must be non-negative integer")
        for key in ("headings",):
            require(errors, isinstance(page.get(key), list), f"browser evidence page.{key} must be a list")
        for key in ("links", "buttons", "buttons_without_name", "inputs", "inputs_without_label", "images", "images_without_alt", "aria_labels"):
            require(errors, isinstance(page.get(key), int) and page.get(key) >= 0, f"browser evidence page.{key} must be non-negative integer")
        require(errors, isinstance(page.get("html_lang"), bool), "browser evidence page.html_lang must be boolean")

    checks = evidence.get("checks")
    require(errors, isinstance(checks, dict), "browser evidence checks must be an object")
    if isinstance(checks, dict):
        missing = [check for check in BROWSER_EVIDENCE_CHECKS if check not in checks]
        require(errors, not missing, f"browser evidence missing checks: {', '.join(missing)}")
        for check, check_report in checks.items():
            require(errors, check in BROWSER_EVIDENCE_CHECKS, f"browser evidence unknown check: {check}")
            require(errors, isinstance(check_report, dict), f"browser evidence checks.{check} must be an object")
            if isinstance(check_report, dict):
                require(errors, check_report.get("status") in BROWSER_EVIDENCE_STATUSES, f"browser evidence checks.{check}.status is invalid")
                require(errors, non_empty_string(check_report.get("summary")), f"browser evidence checks.{check}.summary must be non-empty")
                require(errors, isinstance(check_report.get("evidence"), list), f"browser evidence checks.{check}.evidence must be a list")

    findings = evidence.get("findings")
    require(errors, isinstance(findings, list), "browser evidence findings must be a list")
    high_or_critical = False
    if isinstance(findings, list):
        seen_ids: set[str] = set()
        for index, finding_item in enumerate(findings):
            prefix = f"findings[{index}]"
            require(errors, isinstance(finding_item, dict), f"browser evidence {prefix} must be an object")
            if not isinstance(finding_item, dict):
                continue
            fid = finding_item.get("id")
            require(errors, non_empty_string(fid), f"browser evidence {prefix}.id must be non-empty")
            require(errors, fid not in seen_ids, f"browser evidence {prefix}.id is duplicated: {fid}")
            if non_empty_string(fid):
                seen_ids.add(fid)
            require(errors, finding_item.get("check") in BROWSER_EVIDENCE_CHECKS, f"browser evidence {prefix}.check is invalid")
            severity = finding_item.get("severity")
            require(errors, severity in QUALITY_SEVERITIES, f"browser evidence {prefix}.severity is invalid")
            if severity in QUALITY_FAIL_SEVERITIES:
                high_or_critical = True
            for field in ("summary", "recommendation", "source"):
                require(errors, non_empty_string(finding_item.get(field)), f"browser evidence {prefix}.{field} must be non-empty")

    metrics = evidence.get("metrics")
    require(errors, isinstance(metrics, dict), "browser evidence metrics must be an object")
    if isinstance(metrics, dict):
        for key in (
            "total_findings",
            "critical_findings",
            "high_findings",
            "medium_findings",
            "low_findings",
            "check_pass_count",
            "check_fail_count",
            "check_warning_count",
            "check_not_applicable_count",
        ):
            require(errors, isinstance(metrics.get(key), int) and metrics.get(key) >= 0, f"browser evidence metrics.{key} must be non-negative integer")
        if isinstance(findings, list):
            require(errors, metrics.get("total_findings") == len(findings), "browser evidence metrics.total_findings must match findings length")

    artifacts = evidence.get("artifacts")
    require(errors, isinstance(artifacts, dict), "browser evidence artifacts must be an object")
    if evidence.get("status") == "pass":
        require(errors, not high_or_critical, "passing browser evidence cannot contain critical/high findings")
    if evidence.get("status") == "fail":
        require(errors, high_or_critical, "failing browser evidence must contain at least one critical/high finding")
    return errors


def validate_responsive_matrix_obj(matrix: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("run_id", "status", "required_viewports", "viewports", "findings", "metrics"):
        require(errors, key in matrix, f"responsive matrix missing required field: {key}")
    require(errors, non_empty_string(matrix.get("run_id")), "responsive matrix run_id must be non-empty")
    require(errors, matrix.get("status") in RESPONSIVE_MATRIX_STATUSES, "responsive matrix status must be pass or fail")
    require(
        errors,
        matrix.get("required_viewports") == list(RESPONSIVE_MATRIX_VIEWPORTS),
        "responsive matrix required_viewports must be mobile, tablet, desktop",
    )

    viewports = matrix.get("viewports")
    require(errors, isinstance(viewports, dict), "responsive matrix viewports must be an object")
    if isinstance(viewports, dict):
        missing = [name for name in RESPONSIVE_MATRIX_VIEWPORTS if name not in viewports]
        require(errors, not missing, f"responsive matrix missing viewports: {', '.join(missing)}")
        for name, report in viewports.items():
            prefix = f"viewports.{name}"
            require(errors, name in RESPONSIVE_MATRIX_VIEWPORTS, f"responsive matrix unknown viewport: {name}")
            require(errors, isinstance(report, dict), f"responsive matrix {prefix} must be an object")
            if not isinstance(report, dict):
                continue
            require(errors, report.get("status") in RESPONSIVE_MATRIX_STATUSES, f"responsive matrix {prefix}.status must be pass or fail")
            require(errors, isinstance(report.get("width"), int) and report.get("width") > 0, f"responsive matrix {prefix}.width must be positive")
            require(errors, isinstance(report.get("height"), int) and report.get("height") > 0, f"responsive matrix {prefix}.height must be positive")
            require(errors, non_empty_string(report.get("browser_evidence")), f"responsive matrix {prefix}.browser_evidence must be non-empty")
            require(errors, isinstance(report.get("screenshot"), str), f"responsive matrix {prefix}.screenshot must be a string")
            require(errors, isinstance(report.get("findings"), list), f"responsive matrix {prefix}.findings must be a list")

    findings = matrix.get("findings")
    require(errors, isinstance(findings, list), "responsive matrix findings must be a list")
    if isinstance(findings, list):
        for index, finding_item in enumerate(findings):
            prefix = f"findings[{index}]"
            require(errors, isinstance(finding_item, dict), f"responsive matrix {prefix} must be an object")
            if isinstance(finding_item, dict):
                require(errors, non_empty_string(finding_item.get("viewport")), f"responsive matrix {prefix}.viewport must be non-empty")
                require(errors, non_empty_string(finding_item.get("summary")), f"responsive matrix {prefix}.summary must be non-empty")

    metrics = matrix.get("metrics")
    require(errors, isinstance(metrics, dict), "responsive matrix metrics must be an object")
    if isinstance(metrics, dict):
        for key in ("pass_count", "fail_count", "finding_count"):
            require(errors, isinstance(metrics.get(key), int) and metrics.get(key) >= 0, f"responsive matrix metrics.{key} must be non-negative")

    if matrix.get("status") == "pass":
        require(errors, not findings, "passing responsive matrix cannot contain findings")
    return errors


def validate_quality_report_obj(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("run_id", "spec_id", "status", "upstream_source", "checks", "findings", "metrics", "next_route", "artifacts"):
        require(errors, key in report, f"quality report missing required field: {key}")
    require(errors, non_empty_string(report.get("run_id")), "quality report run_id must be non-empty")
    require(errors, non_empty_string(report.get("spec_id")), "quality report spec_id must be non-empty")
    require(errors, report.get("status") in {"pass", "fail"}, "quality report status must be pass or fail")
    require(errors, report.get("next_route") in SKILLS, "quality report next_route must be a Lodestar skill")

    upstream_source = report.get("upstream_source")
    require(errors, isinstance(upstream_source, dict), "quality report upstream_source must be an object")
    if isinstance(upstream_source, dict):
        require(
            errors,
            upstream_source.get("repo") in {"compound-engineering-plugin", "gstack"},
            "quality report upstream_source.repo must be compound-engineering-plugin or gstack",
        )
        require(errors, non_empty_string(upstream_source.get("adapter")), "quality report upstream_source.adapter must be non-empty")
        require(errors, non_empty_string_list(upstream_source.get("paths")), "quality report upstream_source.paths must be a non-empty string list")

    checks = report.get("checks")
    require(errors, isinstance(checks, dict), "quality report checks must be an object")
    if isinstance(checks, dict):
        missing_checks = [check for check in QUALITY_CHECKS if check not in checks]
        require(errors, not missing_checks, f"quality report missing checks: {', '.join(missing_checks)}")
        for check, check_report in checks.items():
            require(errors, check in QUALITY_CHECKS, f"unknown quality check: {check}")
            require(errors, isinstance(check_report, dict), f"checks.{check} must be an object")
            if not isinstance(check_report, dict):
                continue
            require(errors, check_report.get("status") in QUALITY_CHECK_STATUSES, f"checks.{check}.status is invalid")
            require(errors, non_empty_string(check_report.get("summary")), f"checks.{check}.summary must be non-empty")
            require(errors, isinstance(check_report.get("evidence"), list), f"checks.{check}.evidence must be a list")

    findings = report.get("findings")
    require(errors, isinstance(findings, list), "quality report findings must be a list")
    high_or_critical = False
    if isinstance(findings, list):
        seen_finding_ids: set[str] = set()
        for index, finding_item in enumerate(findings):
            prefix = f"findings[{index}]"
            require(errors, isinstance(finding_item, dict), f"{prefix} must be an object")
            if not isinstance(finding_item, dict):
                continue
            fid = finding_item.get("id")
            require(errors, non_empty_string(fid), f"{prefix}.id must be non-empty")
            require(errors, fid not in seen_finding_ids, f"{prefix}.id is duplicated: {fid}")
            if non_empty_string(fid):
                seen_finding_ids.add(fid)
            require(errors, finding_item.get("check") in QUALITY_CHECKS, f"{prefix}.check is invalid")
            severity = finding_item.get("severity")
            require(errors, severity in QUALITY_SEVERITIES, f"{prefix}.severity is invalid")
            if severity in QUALITY_FAIL_SEVERITIES:
                high_or_critical = True
            require(
                errors,
                finding_item.get("owner") in {"fixer", "debrief", "amend-advisor", "handoff", "human"},
                f"{prefix}.owner must be fixer, debrief, amend-advisor, handoff, or human",
            )
            for field in ("summary", "recommendation", "source"):
                require(errors, non_empty_string(finding_item.get(field)), f"{prefix}.{field} must be non-empty")

    metrics = report.get("metrics")
    require(errors, isinstance(metrics, dict), "quality report metrics must be an object")
    if isinstance(metrics, dict):
        for key in (
            "total_findings",
            "critical_findings",
            "high_findings",
            "medium_findings",
            "low_findings",
            "check_pass_count",
            "check_fail_count",
            "check_warning_count",
            "check_not_applicable_count",
        ):
            require(errors, isinstance(metrics.get(key), int) and metrics.get(key) >= 0, f"metrics.{key} must be a non-negative integer")
        if isinstance(findings, list):
            require(errors, metrics.get("total_findings") == len(findings), "metrics.total_findings must match findings length")

    artifacts = report.get("artifacts")
    require(errors, isinstance(artifacts, dict), "quality report artifacts must be an object")
    if isinstance(artifacts, dict):
        for key in ("locked_spec", "execution_plan", "build_evidence", "review_report", "browser_evidence"):
            require(errors, non_empty_string(artifacts.get(key)), f"quality report artifacts.{key} must be non-empty")

    if report.get("status") == "pass":
        require(errors, not high_or_critical, "passing quality report cannot contain critical/high findings")
        require(errors, report.get("next_route") == "lodestar-dock", "passing quality report must route to lodestar-dock")
    if report.get("status") == "fail":
        require(errors, high_or_critical, "failing quality report must contain at least one critical/high finding")
        require(errors, report.get("next_route") != "lodestar-dock", "failing quality report cannot route to lodestar-dock")
    return errors


def validate_debrief_obj(synthesis: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "run_id",
        "spec_id",
        "status",
        "upstream_source",
        "trigger",
        "failure_clusters",
        "root_cause_hypothesis",
        "what_did_not_work",
        "next_fix_strategy",
        "verification_plan",
        "learning_note",
        "intent_impact",
        "return_route",
        "forbidden_routes",
        "artifacts",
    ]
    for key in required:
        require(errors, key in synthesis, f"CE synthesis missing required field: {key}")
    require(errors, non_empty_string(synthesis.get("run_id")), "CE synthesis run_id must be non-empty")
    require(errors, non_empty_string(synthesis.get("spec_id")), "CE synthesis spec_id must be non-empty")
    require(errors, synthesis.get("status") in CE_SYNTHESIS_STATUSES, "CE synthesis status is invalid")
    require(errors, synthesis.get("return_route") in CE_RETURN_ROUTES, "CE synthesis return_route must be fixer, implementer, or amend advisor")
    require(errors, synthesis.get("return_route") not in CE_FORBIDDEN_ROUTES, "CE synthesis cannot return to review or handoff")

    upstream_source = synthesis.get("upstream_source")
    require(errors, isinstance(upstream_source, dict), "CE synthesis upstream_source must be an object")
    if isinstance(upstream_source, dict):
        require(errors, upstream_source.get("repo") == "compound-engineering-plugin", "CE synthesis upstream_source.repo must be compound-engineering-plugin")
        require(errors, non_empty_string(upstream_source.get("adapter")), "CE synthesis upstream_source.adapter must be non-empty")
        require(errors, non_empty_string_list(upstream_source.get("paths")), "CE synthesis upstream_source.paths must be a non-empty string list")

    trigger = synthesis.get("trigger")
    require(errors, isinstance(trigger, dict), "CE synthesis trigger must be an object")
    if isinstance(trigger, dict):
        require(errors, trigger.get("kind") in CE_TRIGGER_KINDS, "CE synthesis trigger.kind is invalid")
        require(errors, trigger.get("severity") in QUALITY_SEVERITIES, "CE synthesis trigger.severity is invalid")
        for field in ("summary", "source"):
            require(errors, non_empty_string(trigger.get(field)), f"CE synthesis trigger.{field} must be non-empty")

    clusters = synthesis.get("failure_clusters")
    require(errors, isinstance(clusters, list) and bool(clusters), "CE synthesis failure_clusters must be non-empty")
    repeated_cluster = False
    if isinstance(clusters, list):
        seen_cluster_ids: set[str] = set()
        for index, cluster in enumerate(clusters):
            prefix = f"failure_clusters[{index}]"
            require(errors, isinstance(cluster, dict), f"{prefix} must be an object")
            if not isinstance(cluster, dict):
                continue
            cid = cluster.get("id")
            require(errors, non_empty_string(cid), f"{prefix}.id must be non-empty")
            require(errors, cid not in seen_cluster_ids, f"{prefix}.id is duplicated: {cid}")
            if non_empty_string(cid):
                seen_cluster_ids.add(cid)
            kind = cluster.get("kind")
            require(errors, kind in CE_TRIGGER_KINDS, f"{prefix}.kind is invalid")
            repeated_cluster = repeated_cluster or kind == "repeated_failure"
            require(errors, cluster.get("severity") in QUALITY_SEVERITIES, f"{prefix}.severity is invalid")
            require(errors, non_empty_string(cluster.get("summary")), f"{prefix}.summary must be non-empty")
            require(errors, isinstance(cluster.get("evidence"), list) and bool(cluster.get("evidence")), f"{prefix}.evidence must be non-empty")
            require(errors, isinstance(cluster.get("owners"), list) and bool(cluster.get("owners")), f"{prefix}.owners must be non-empty")

    hypothesis = synthesis.get("root_cause_hypothesis")
    require(errors, isinstance(hypothesis, dict), "CE synthesis root_cause_hypothesis must be an object")
    if isinstance(hypothesis, dict):
        require(errors, non_empty_string(hypothesis.get("summary")), "CE synthesis root_cause_hypothesis.summary must be non-empty")
        require(errors, hypothesis.get("confidence") in CONFIDENCE, "CE synthesis root_cause_hypothesis.confidence is invalid")
        require(errors, isinstance(hypothesis.get("supporting_evidence"), list) and bool(hypothesis.get("supporting_evidence")), "CE synthesis root_cause_hypothesis.supporting_evidence must be non-empty")

    require(errors, isinstance(synthesis.get("what_did_not_work"), list), "CE synthesis what_did_not_work must be a list")

    strategy = synthesis.get("next_fix_strategy")
    require(errors, isinstance(strategy, dict), "CE synthesis next_fix_strategy must be an object")
    if isinstance(strategy, dict):
        require(errors, strategy.get("owner") in {"fixer", "implementer", "amend-advisor"}, "CE synthesis next_fix_strategy.owner is invalid")
        require(errors, isinstance(strategy.get("steps"), list) and bool(strategy.get("steps")), "CE synthesis next_fix_strategy.steps must be non-empty")

    require(errors, isinstance(synthesis.get("verification_plan"), list) and bool(synthesis.get("verification_plan")), "CE synthesis verification_plan must be non-empty")

    learning_note = synthesis.get("learning_note")
    require(errors, isinstance(learning_note, dict), "CE synthesis learning_note must be an object")
    if isinstance(learning_note, dict):
        require(errors, learning_note.get("status") in CE_LEARNING_STATUSES, "CE synthesis learning_note.status is invalid")
        require(errors, non_empty_string(learning_note.get("key")), "CE synthesis learning_note.key must be non-empty")
        require(errors, non_empty_string(learning_note.get("prevention_rule")), "CE synthesis learning_note.prevention_rule must be non-empty")
        if repeated_cluster:
            require(errors, learning_note.get("status") in {"required", "written"}, "repeated CE failure requires a learning note")

    intent_impact = synthesis.get("intent_impact")
    require(errors, isinstance(intent_impact, dict), "CE synthesis intent_impact must be an object")
    if isinstance(intent_impact, dict):
        require(errors, isinstance(intent_impact.get("may_change_product_intent"), bool), "CE synthesis intent_impact.may_change_product_intent must be boolean")
        require(errors, isinstance(intent_impact.get("amendment_required"), bool), "CE synthesis intent_impact.amendment_required must be boolean")
        require(errors, non_empty_string(intent_impact.get("reason")), "CE synthesis intent_impact.reason must be non-empty")
        if synthesis.get("return_route") == "lodestar-course-correct":
            require(errors, intent_impact.get("amendment_required") is True, "amend advisor route requires amendment_required true")

    forbidden_routes = synthesis.get("forbidden_routes")
    require(errors, isinstance(forbidden_routes, list), "CE synthesis forbidden_routes must be a list")
    if isinstance(forbidden_routes, list):
        for route in CE_FORBIDDEN_ROUTES:
            require(errors, route in forbidden_routes, f"CE synthesis forbidden_routes must include {route}")

    artifacts = synthesis.get("artifacts")
    require(errors, isinstance(artifacts, dict), "CE synthesis artifacts must be an object")
    if isinstance(artifacts, dict):
        for key in ("review_report", "quality_report", "execution_plan"):
            require(errors, key in artifacts, f"CE synthesis artifacts missing key: {key}")
    if synthesis.get("status") == "ready":
        require(errors, synthesis.get("return_route") in CE_RETURN_ROUTES, "ready CE synthesis must have a valid return route")
    return errors
