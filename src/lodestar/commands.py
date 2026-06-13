"""CLI command handlers (command_* functions)."""
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

from .dryrun import *  # noqa: F401,F403
from .execution import *  # noqa: F401,F403


def check_removed_coarse_skills(skills_dir: Path) -> list[str]:
    errors = []
    for skill in REMOVED_COARSE_SKILLS:
        if (skills_dir / skill).exists():
            errors.append(f"old coarse skill still exists: {skill}")
    for skill in ("lodestar-lock", "lodestar-debrief"):
        body = (skills_dir / skill / "SKILL.md").read_text(encoding="utf-8")
        if "compatibility" in body.lower() or "wrapper" in body.lower():
            errors.append(f"{skill} still looks like a compatibility wrapper")
    return errors


def command_validate(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.path)
    warnings: list[str] = []
    if args.kind == "locked-spec":
        fail_if_errors(validate_locked_spec_obj(read_json(path)))
    elif args.kind == "task-graph":
        spec = read_json(Path(args.spec)) if args.spec else None
        task_graph = read_json(path)
        fail_if_errors(validate_task_graph_obj(task_graph, spec))
        warnings = task_graph_parallel_warnings(task_graph)
    elif args.kind == "build-evidence":
        fail_if_errors(validate_build_evidence_obj(read_json(path)))
    elif args.kind == "review-report":
        fail_if_errors(validate_review_report_obj(read_json(path)))
    elif args.kind == "amendment-request":
        fail_if_errors(validate_amendment_request_obj(read_json(path)))
    elif args.kind == "final-handoff":
        fail_if_errors(validate_final_handoff_obj(read_json(path)))
    elif args.kind == "proof-bundle":
        fail_if_errors(validate_proof_bundle_obj(read_json(path)))
    elif args.kind == "checklist-report":
        fail_if_errors(validate_spec_gate_report_obj(read_json(path)))
    elif args.kind == "browser-evidence":
        fail_if_errors(validate_browser_evidence_obj(read_json(path)))
    elif args.kind == "quality-report":
        fail_if_errors(validate_quality_report_obj(read_json(path)))
    elif args.kind == "debrief":
        fail_if_errors(validate_debrief_obj(read_json(path)))
    elif args.kind == "execution-plan":
        fail_if_errors(validate_execution_plan_obj(read_json(path)))
    elif args.kind == "task-state":
        fail_if_errors(validate_task_state_obj(read_json(path)))
    elif args.kind == "agent-dispatch":
        fail_if_errors(validate_agent_dispatch_obj(read_json(path)))
    elif args.kind == "agent-dispatch-batch":
        fail_if_errors(validate_agent_dispatch_batch_obj(read_json(path)))
    else:
        raise LodestarError(f"Unknown validation kind: {args.kind}")
    result = {"status": "pass", "kind": args.kind, "path": args.path}
    if warnings:
        result["warnings"] = warnings
    return result


def command_spec_gate(args: argparse.Namespace) -> dict[str, Any]:
    spec = read_json(Path(args.spec))
    ux_lock_text = read_optional_text(Path(args.ux_lock), "UX lock") if args.ux_lock else ""
    decision_log = read_decision_log(Path(args.decision_log)) if args.decision_log else []
    report = build_spec_gate_report(spec, ux_lock_text, decision_log)
    fail_if_errors(validate_spec_gate_report_obj(report))
    write_json(Path(args.out), report)
    if report["status"] == "fail" and not args.report_only:
        raise LodestarError(f"Spec gate failed; report written to {args.out}; next_route={report['next_route']}")
    return {"status": report["status"], "path": args.out, "next_route": report["next_route"], "metrics": report["metrics"]}


def artifact_path(run_dir: Path, explicit: str | None, default_name: str) -> Path:
    if explicit:
        return Path(explicit)
    return run_dir / default_name


def command_quality_gate(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = Path(args.run_dir)
    spec_path = artifact_path(run_dir, args.spec, "locked-spec.json")
    execution_plan_path = artifact_path(run_dir, args.execution_plan, "execution-plan.json")
    build_path = artifact_path(run_dir, args.build, "build-evidence.json")
    review_path = artifact_path(run_dir, args.review, "review-report.json")
    ux_lock_path = artifact_path(run_dir, args.ux_lock, "shape-lock.md")
    proof_bundle_path = artifact_path(run_dir, args.proof_bundle, "proof-bundle.json")
    browser_evidence_path = artifact_path(run_dir, args.browser_evidence, "browser-evidence.json")

    spec = read_json(spec_path)
    execution_plan = read_json(execution_plan_path)
    build_evidence = read_json(build_path)
    review_report = read_json(review_path)
    ux_lock_text = read_optional_text(ux_lock_path, "UX lock")
    proof_bundle = read_optional_json(proof_bundle_path, "Proof bundle")
    browser_evidence = read_optional_json(browser_evidence_path, "Browser evidence") if browser_evidence_path.exists() else {}
    run_id = args.run_id or execution_plan.get("run_id") or proof_bundle.get("run_id") or "quality-run"

    fail_if_errors(validate_locked_spec_obj(spec))
    fail_if_errors(validate_execution_plan_obj(execution_plan))
    fail_if_errors(validate_build_evidence_obj(build_evidence))
    fail_if_errors(validate_review_report_obj(review_report))
    if browser_evidence:
        fail_if_errors(validate_browser_evidence_obj(browser_evidence))

    report = build_quality_report(
        str(run_id),
        spec,
        execution_plan,
        build_evidence,
        review_report,
        ux_lock_text,
        proof_bundle,
        browser_evidence,
        {
            "locked_spec": str(spec_path),
            "execution_plan": str(execution_plan_path),
            "build_evidence": str(build_path),
            "review_report": str(review_path),
            "ux_lock": str(ux_lock_path),
            "browser_evidence": str(browser_evidence_path),
            "proof_bundle": str(proof_bundle_path),
        },
    )
    fail_if_errors(validate_quality_report_obj(report))
    write_json(Path(args.out), report)
    if report["status"] == "fail" and not args.report_only:
        raise LodestarError(f"Quality gate failed; report written to {args.out}; next_route={report['next_route']}")
    return {"status": report["status"], "path": args.out, "next_route": report["next_route"], "metrics": report["metrics"]}


def command_browser_collect(args: argparse.Namespace) -> dict[str, Any]:
    target_count = sum(1 for target in (args.url, args.html, args.snapshot) if bool(target))
    if target_count != 1:
        raise LodestarError("Provide exactly one browser target: --url, --html, or --snapshot")
    run_id = args.run_id or "browser-run"
    snapshot_page = None
    snapshot_console_errors: list[str] = []
    snapshot_screenshot = ""
    if args.url:
        html_text, load_summary = fetch_url_text(args.url, args.timeout)
        mode = "url"
        source = args.url
    elif args.html:
        html_path = Path(args.html)
        try:
            html_text = html_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise LodestarError(f"HTML target not found: {html_path}") from exc
        mode = "html"
        source = str(html_path)
        load_summary = "Loaded HTML artifact."
    else:
        snapshot_path = Path(args.snapshot)
        snapshot = read_json(snapshot_path)
        snapshot_page = page_from_rendered_snapshot(snapshot)
        snapshot_console_errors = rendered_snapshot_console_errors(snapshot)
        snapshot_screenshot = rendered_snapshot_screenshot(snapshot)
        html_text = ""
        mode = "snapshot"
        source = str(snapshot_path)
        load_summary = "Loaded rendered browser snapshot."

    evidence = build_browser_evidence(
        run_id=run_id,
        mode=mode,
        source=source,
        html_text=html_text,
        expected_text=args.expect_text or [],
        viewport_name=args.viewport,
        screenshot_path=args.screenshot or snapshot_screenshot,
        console_errors_path=args.console_errors,
        console_errors=snapshot_console_errors,
        snapshot_page=snapshot_page,
        load_summary=load_summary,
    )
    fail_if_errors(validate_browser_evidence_obj(evidence))
    write_json(Path(args.out), evidence)
    if evidence["status"] == "fail" and not args.report_only:
        raise LodestarError(f"Browser evidence failed; report written to {args.out}")
    return {"status": evidence["status"], "path": args.out, "target": evidence["target"], "metrics": evidence["metrics"]}


def command_ce_synthesize(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = Path(args.run_dir)
    spec_path = artifact_path(run_dir, args.spec, "locked-spec.json")
    execution_plan_path = artifact_path(run_dir, args.execution_plan, "execution-plan.json")
    review_path = artifact_path(run_dir, args.review, "review-report.json")
    quality_path = artifact_path(run_dir, args.quality, "quality-report.json")
    build_path = artifact_path(run_dir, args.build, "build-evidence.json")

    spec = read_json(spec_path)
    execution_plan = read_json(execution_plan_path)
    review_report = read_json(review_path)
    quality_report = read_optional_json(quality_path, "Quality report") if quality_path.exists() else {}
    build_evidence = read_optional_json(build_path, "Build evidence") if build_path.exists() else {}
    run_id = args.run_id or execution_plan.get("run_id") or "ce-run"

    fail_if_errors(validate_locked_spec_obj(spec))
    fail_if_errors(validate_execution_plan_obj(execution_plan))
    fail_if_errors(validate_review_report_obj(review_report))
    if quality_report:
        fail_if_errors(validate_quality_report_obj(quality_report))
    if build_evidence:
        fail_if_errors(validate_build_evidence_obj(build_evidence))

    synthesis = build_debrief(
        str(run_id),
        spec,
        execution_plan,
        review_report,
        quality_report,
        build_evidence,
        {
            "review_report": str(review_path),
            "quality_report": str(quality_path),
            "execution_plan": str(execution_plan_path),
            "build_evidence": str(build_path),
        },
    )
    fail_if_errors(validate_debrief_obj(synthesis))
    write_json(Path(args.out), synthesis)
    if args.brief_out:
        write_text(Path(args.brief_out), render_debrief_brief(synthesis))
    if synthesis["status"] == "blocked" and not args.report_only:
        raise LodestarError(f"CE synthesis blocked; report written to {args.out}; missing concrete failure trigger")
    return {
        "status": synthesis["status"],
        "path": args.out,
        "brief": args.brief_out,
        "return_route": synthesis["return_route"],
        "trigger": synthesis["trigger"],
    }


def command_upstream_check(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    upstream_map = read_json(Path(args.map) if args.map else root / "references" / "upstream-map.json")
    fail_if_errors(validate_upstream_map_obj(upstream_map, root))
    files = 0
    for repo in upstream_map["repositories"]:
        for imported in repo["imported_roots"]:
            imported_path = root / imported
            if imported_path.is_file():
                files += 1
            else:
                files += len([path for path in imported_path.rglob("*") if path.is_file()])
    return {
        "status": "pass",
        "strategy": upstream_map["strategy"],
        "repository_count": len(upstream_map["repositories"]),
        "imported_file_count": files,
        "repositories": [repo["id"] for repo in upstream_map["repositories"]],
    }


def command_init_run(args: argparse.Namespace) -> dict[str, Any]:
    return init_run(Path(args.root), args.run_id, args.out)


def command_runner_step(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.state)
    state = read_json(path) if path.exists() else new_runner_state()
    state = apply_runner_event(state, args.event, args.evidence)
    out = Path(args.out) if args.out else path
    write_json(out, state)
    return {"status": "pass", "path": str(out), "runner_state": state["runner_state"], "state": state}


def command_negative_checks(args: argparse.Namespace) -> dict[str, Any]:
    checks = [
        ("INTAKE blocks ux-approved", {"runner_state": "INTAKE"}, "ux-approved"),
        ("reviewer blocks code-edit", {"runner_state": "REVIEWING"}, "code-edit"),
        ("reviewer blocks direct handoff", {"runner_state": "REVIEWING"}, "handoff-ready"),
        ("merge-ready blocks direct handoff", {"runner_state": "MERGE_READY"}, "handoff-ready"),
        ("QA blocks direct handoff", {"runner_state": "QA_READY"}, "handoff-ready"),
        ("proof blocks direct handoff", {"runner_state": "PROOF_READY"}, "handoff-ready"),
        ("debrief blocks handoff-ready", {"runner_state": "COMPOUNDING"}, "handoff-ready"),
        ("amend advisor blocks auto-approve", {"runner_state": "AMENDMENT_PENDING"}, "auto-approve"),
    ]
    passed = []
    errors = []
    for name, state, event in checks:
        try:
            apply_runner_event(state, event, name)
        except LodestarError:
            passed.append(name)
        else:
            errors.append(f"negative check failed: {name}")

    try:
        review_approved_runner = apply_runner_event({"runner_state": "REVIEWING"}, "reviewer-approve", "negative runner merge setup")
        if review_approved_runner.get("runner_state") == "MERGE_READY":
            passed.append("review approve routes to merge gate before handoff")
        else:
            errors.append("negative check failed: review approve did not route to merge gate")
    except LodestarError as exc:
        errors.append(f"review approve merge route failed unexpectedly: {exc}")

    try:
        handoff_runner = {"runner_state": "REVIEWING", "history": []}
        for event in ("reviewer-approve", "merge-pass", "quality-pass", "proof-pass"):
            handoff_runner = apply_runner_event(handoff_runner, event, f"runner handoff path {event}")
        if handoff_runner.get("runner_state") == "HANDOFF_READY":
            passed.append("runner reaches handoff only after merge quality proof")
        else:
            errors.append("negative check failed: runner did not reach handoff after merge quality proof")
    except LodestarError as exc:
        errors.append(f"runner handoff path failed unexpectedly: {exc}")

    errors.extend(check_removed_coarse_skills(Path(args.skills_dir)))

    spec_negative_cases: list[tuple[str, dict[str, Any]]] = []

    missing_ux_spec = fake_locked_spec()
    missing_ux_spec["product_shape"]["approved_preview"] = False
    spec_negative_cases.append(("spec gate blocks missing UX approval", missing_ux_spec))

    placeholder_spec = fake_locked_spec()
    placeholder_spec["intent"] = "NEEDS CLARIFICATION: decide the real product intent before implementation."
    spec_negative_cases.append(("spec gate blocks unresolved placeholders", placeholder_spec))

    untestable_spec = fake_locked_spec()
    untestable_spec["success_criteria"][0]["testable"] = False
    spec_negative_cases.append(("spec gate blocks untestable success criteria", untestable_spec))

    for name, spec in spec_negative_cases:
        report = build_spec_gate_report(spec, "# UX Lock\n\nApproved by: negative-check\n", [{"status": "accepted"}])
        try:
            fail_if_errors(validate_spec_gate_report_obj(report))
        except LodestarError as exc:
            errors.append(f"{name} produced an invalid report: {exc}")
            continue
        if report["status"] == "fail":
            passed.append(name)
        else:
            errors.append(f"negative check failed: {name}")

    fake_task = fake_task_graph()["tasks"][0]
    base_task_state = new_task_state(fake_task, "negative-run", "dryrun-spec", Path(".lodestar/worktrees/T1"))
    task_negative_cases = [
        ("task loop blocks review before implementation", base_task_state, "reviewer-approve"),
        ("task loop blocks code-edit event in review", {**base_task_state, "state": "REVIEWING", "status": "in-progress", "next_allowed_events": task_allowed_events("REVIEWING")}, "code-edit"),
        ("task loop blocks CE direct review", {**base_task_state, "state": "COMPOUNDING", "status": "in-progress", "next_allowed_events": task_allowed_events("COMPOUNDING")}, "reviewer-approve"),
        ("task loop blocks done task restart", {**base_task_state, "state": "TASK_DONE", "status": "done", "next_allowed_events": task_allowed_events("TASK_DONE")}, "implementation-started"),
    ]
    for name, state, event in task_negative_cases:
        try:
            fail_if_errors(validate_task_state_obj(state))
            apply_task_event(state, event, name)
        except LodestarError:
            passed.append(name)
        else:
            errors.append(f"negative check failed: {name}")

    review_state = apply_task_event(base_task_state, "implementation-started", "negative review setup")
    review_state = apply_task_event(review_state, "implementation-ready", "negative review setup")
    review_state = apply_task_event(review_state, "build-pass", "negative review setup")
    review_dispatch = build_agent_dispatch(Path(".lodestar/negative"), review_state, "single-agent-fallback", "locked-spec.json", "task-graph.json")
    invalid_review_dispatch = json.loads(json.dumps(review_dispatch))
    invalid_review_dispatch["route"].pop("review_stages", None)
    try:
        fail_if_errors(validate_agent_dispatch_obj(invalid_review_dispatch))
    except LodestarError:
        passed.append("reviewer dispatch requires spec then code quality review")
    else:
        errors.append("negative check failed: reviewer dispatch requires spec then code quality review")

    merge_state = apply_task_event(review_state, "reviewer-approve", "negative merge setup")
    try:
        merge_failed = apply_task_event(merge_state, "merge-conflict", "negative merge conflict")
        if merge_failed["state"] == "FIXING":
            passed.append("merge conflict routes to fixer")
        else:
            errors.append("negative check failed: merge conflict routes to fixer")
    except LodestarError as exc:
        errors.append(f"merge conflict route was invalid: {exc}")

    batch_graph = {
        "spec_id": "dryrun-spec",
        "status": "ready",
        "tasks": [
            {
                "id": "T1",
                "title": "Parallel root one",
                "branch": "task/root-one",
                "role": "implementer",
                "acceptance_criteria": ["SC1 is covered."],
                "covers": ["SC1", "AS1"],
                "dependencies": [],
                "parallel_group": "root",
                "write_scope": ["Sources/RootOne"],
                "merge_risk": "low",
            },
            {
                "id": "T2",
                "title": "Parallel root two",
                "branch": "task/root-two",
                "role": "implementer",
                "acceptance_criteria": ["SC2 is covered."],
                "covers": ["SC2", "AS2"],
                "dependencies": [],
                "parallel_group": "root",
                "write_scope": ["Sources/RootTwo"],
                "merge_risk": "low",
            },
            {
                "id": "T3",
                "title": "Blocked dependent task",
                "branch": "task/dependent",
                "role": "implementer",
                "acceptance_criteria": ["Dependent work waits for T1."],
                "covers": ["SC1"],
                "dependencies": ["T1"],
                "parallel_group": "dependent",
                "write_scope": ["Sources/Dependent"],
                "merge_risk": "medium",
            },
        ],
    }
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        run_dir = temp_root / "run"
        try:
            init_execution_run(batch_graph, fake_locked_spec(), run_dir, temp_root, Path("worktrees"), "negative-batch")
            batch_result = dispatch_execution_batch(run_dir, "subagent", "locked-spec.json", "task-graph.json")
            batch = batch_result["batch"]
            if batch["metrics"]["dispatchable"] == 2 and {item["task_id"] for item in batch["items"]} == {"T1", "T2"}:
                passed.append("batch dispatch starts all dependency-free tasks")
            else:
                errors.append("negative check failed: batch dispatch starts all dependency-free tasks")
            if batch["blocked_ready"] == [{"task_id": "T3", "pending_dependencies": ["T1"]}]:
                passed.append("batch dispatch blocks pending dependencies")
            else:
                errors.append("negative check failed: batch dispatch blocks pending dependencies")
            fail_if_errors(validate_agent_dispatch_batch_obj(batch))
        except LodestarError as exc:
            errors.append(f"batch dispatch negative setup failed: {exc}")

    quality_base_spec = fake_locked_spec()
    quality_base_plan = fake_done_execution_plan()
    quality_base_build = fake_build_evidence("pass")
    quality_base_review = fake_review_report("approved")
    quality_base_proof = new_proof_bundle("dry-run", "pass")
    quality_base_proof["artifacts"] = {
        "ux_guard": "shape-lock.md",
        "build_evidence": "build-evidence.json",
        "review_report": "review-report.json",
        "quality_report": "quality-report.json",
        "browser_evidence": "browser-evidence.json",
        "proof_bundle": "proof-bundle.json",
    }
    quality_base_browser = build_browser_evidence(
        run_id="negative-run",
        mode="html",
        source="negative-shape.html",
        html_text='<!doctype html><html lang="en"><title>Negative QA</title><main><h1>UX Preview Approved</h1></main></html>',
        expected_text=["UX Preview Approved"],
    )
    quality_negative_cases: list[tuple[str, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], str, dict[str, Any]]] = []

    failed_build = fake_build_evidence("fail")
    quality_negative_cases.append(
        (
            "quality gate blocks failed build evidence",
            quality_base_spec,
            quality_base_plan,
            failed_build,
            quality_base_review,
            "# UX Lock\n\nApproved by: negative-check\n",
            quality_base_proof,
        )
    )

    edited_review = fake_review_report("approved")
    edited_review["code_edits_made"] = True
    quality_negative_cases.append(
        (
            "quality gate blocks reviewer code edits",
            quality_base_spec,
            quality_base_plan,
            quality_base_build,
            edited_review,
            "# UX Lock\n\nApproved by: negative-check\n",
            quality_base_proof,
        )
    )

    incomplete_plan = json.loads(json.dumps(quality_base_plan))
    incomplete_plan["status"] = "in-progress"
    incomplete_plan["metrics"]["done"] = 1
    incomplete_plan["metrics"]["in_progress"] = 1
    incomplete_plan["tasks"][1]["state"] = "BUILDING"
    incomplete_plan["tasks"][1]["status"] = "in-progress"
    quality_negative_cases.append(
        (
            "quality gate blocks incomplete execution plan",
            quality_base_spec,
            incomplete_plan,
            quality_base_build,
            quality_base_review,
            "# UX Lock\n\nApproved by: negative-check\n",
            quality_base_proof,
        )
    )

    quality_negative_cases.append(
        (
            "quality gate blocks missing UX lock",
            quality_base_spec,
            quality_base_plan,
            quality_base_build,
            quality_base_review,
            "",
            quality_base_proof,
        )
    )

    for name, spec, execution_plan, build_evidence, review_report, ux_lock_text, proof_bundle in quality_negative_cases:
        report = build_quality_report("negative-run", spec, execution_plan, build_evidence, review_report, ux_lock_text, proof_bundle, quality_base_browser)
        try:
            fail_if_errors(validate_quality_report_obj(report))
        except LodestarError as exc:
            errors.append(f"{name} produced an invalid report: {exc}")
            continue
        if report["status"] == "fail":
            passed.append(name)
        else:
            errors.append(f"negative check failed: {name}")

    passing_quality = build_quality_report(
        "negative-run",
        quality_base_spec,
        quality_base_plan,
        quality_base_build,
        quality_base_review,
        "# UX Lock\n\nApproved by: negative-check\n",
        quality_base_proof,
        quality_base_browser,
    )

    failed_browser = build_browser_evidence(
        run_id="negative-run",
        mode="html",
        source="negative-missing-text.html",
        html_text='<!doctype html><html lang="en"><title>Negative QA</title><main><h1>Rendered Surface</h1></main></html>',
        expected_text=["Approved Surface"],
    )
    try:
        fail_if_errors(validate_browser_evidence_obj(failed_browser))
        if failed_browser["status"] == "fail":
            passed.append("browser collect blocks missing expected text")
        else:
            errors.append("negative check failed: browser collect blocks missing expected text")
    except LodestarError as exc:
        errors.append(f"browser missing text produced invalid evidence: {exc}")

    failed_snapshot_browser = build_browser_evidence(
        run_id="negative-run",
        mode="snapshot",
        source="negative-rendered-snapshot.json",
        html_text="",
        expected_text=["Approved Surface"],
        snapshot_page=page_from_rendered_snapshot(
            {
                "title": "Negative QA",
                "text": "Approved Surface",
                "headings": ["Approved Surface"],
                "html_lang": True,
            }
        ),
        console_errors=["ReferenceError: hydrate is not defined"],
    )
    try:
        fail_if_errors(validate_browser_evidence_obj(failed_snapshot_browser))
        if failed_snapshot_browser["status"] == "fail":
            passed.append("browser collect blocks rendered snapshot console errors")
        else:
            errors.append("negative check failed: browser collect blocks rendered snapshot console errors")
    except LodestarError as exc:
        errors.append(f"snapshot console error produced invalid evidence: {exc}")

    browser_failed_quality = build_quality_report(
        "negative-run",
        quality_base_spec,
        quality_base_plan,
        quality_base_build,
        quality_base_review,
        "# UX Lock\n\nApproved by: negative-check\n",
        quality_base_proof,
        failed_browser,
    )
    try:
        fail_if_errors(validate_quality_report_obj(browser_failed_quality))
        if browser_failed_quality["status"] == "fail":
            passed.append("quality gate blocks failed browser evidence")
        else:
            errors.append("negative check failed: quality gate blocks failed browser evidence")
    except LodestarError as exc:
        errors.append(f"failed browser quality produced invalid report: {exc}")
    no_trigger_ce = build_debrief("negative-run", quality_base_spec, quality_base_plan, quality_base_review, passing_quality, quality_base_build)
    try:
        fail_if_errors(validate_debrief_obj(no_trigger_ce))
        if no_trigger_ce["status"] == "blocked":
            passed.append("CE synthesis blocks missing trigger evidence")
        else:
            errors.append("negative check failed: CE synthesis blocks missing trigger evidence")
    except LodestarError as exc:
        errors.append(f"CE missing trigger produced invalid report: {exc}")

    rejected_review = fake_review_report("rejected")
    ready_ce = build_debrief("negative-run", quality_base_spec, quality_base_plan, rejected_review, passing_quality, quality_base_build)
    invalid_handoff_ce = json.loads(json.dumps(ready_ce))
    invalid_handoff_ce["return_route"] = "lodestar-dock"
    try:
        fail_if_errors(validate_debrief_obj(invalid_handoff_ce))
    except LodestarError:
        passed.append("CE synthesis blocks direct handoff route")
    else:
        errors.append("negative check failed: CE synthesis blocks direct handoff route")

    invalid_amend_ce = json.loads(json.dumps(ready_ce))
    invalid_amend_ce["return_route"] = "lodestar-course-correct"
    invalid_amend_ce["intent_impact"]["amendment_required"] = False
    try:
        fail_if_errors(validate_debrief_obj(invalid_amend_ce))
    except LodestarError:
        passed.append("CE synthesis blocks amendment route without amendment flag")
    else:
        errors.append("negative check failed: CE synthesis blocks amendment route without amendment flag")

    repeated_ce = build_debrief("negative-run", quality_base_spec, quality_base_plan, rejected_review, passing_quality, quality_base_build)
    repeated_ce["failure_clusters"].append(
        {
            "id": "CE-999",
            "kind": "repeated_failure",
            "severity": "high",
            "summary": "Repeated failure without learning note should be blocked.",
            "evidence": ["execution-plan.tasks.T1.attempts"],
            "owners": ["debrief"],
        }
    )
    repeated_ce["learning_note"]["status"] = "not-needed"
    try:
        fail_if_errors(validate_debrief_obj(repeated_ce))
    except LodestarError:
        passed.append("CE synthesis requires learning note for repeated failure")
    else:
        errors.append("negative check failed: CE synthesis requires learning note for repeated failure")

    fail_if_errors(errors)
    return {"status": "pass", "checks": passed, "old_coarse_wrappers_removed": True}


def command_advisor(args: argparse.Namespace) -> dict[str, Any]:
    issue = args.issue
    if args.issue_file:
        issue = Path(args.issue_file).read_text(encoding="utf-8")
    return advisor_route(issue, args.simulate)


def command_worktree_plan(args: argparse.Namespace) -> dict[str, Any]:
    task_graph = read_json(Path(args.task_graph))
    fail_if_errors(validate_task_graph_obj(task_graph))
    repo = Path(args.repo).resolve()
    if args.ensure_repo:
        ensure_git_repo(repo)
    plan = worktree_plan(task_graph, repo, Path(args.worktrees).resolve())
    if args.create:
        ensure_git_repo(repo)
        create_worktrees(plan)
        plan["created"] = True
    if args.out:
        write_json(Path(args.out), plan)
    return {"status": "pass", "plan": plan}


def command_execution_init(args: argparse.Namespace) -> dict[str, Any]:
    task_graph = read_json(Path(args.task_graph))
    spec = read_json(Path(args.spec))
    run_id = args.run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    return init_execution_run(
        task_graph=task_graph,
        spec=spec,
        run_dir=Path(args.run_dir),
        repo=Path(args.repo).resolve(),
        worktrees_dir=Path(args.worktrees),
        run_id=run_id,
    )


def command_execution_start(args: argparse.Namespace) -> dict[str, Any]:
    task_graph = read_json(Path(args.task_graph))
    spec = read_json(Path(args.spec))
    run_id = args.run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    init_result = init_execution_run(
        task_graph=task_graph,
        spec=spec,
        run_dir=Path(args.run_dir),
        repo=Path(args.repo).resolve(),
        worktrees_dir=Path(args.worktrees),
        run_id=run_id,
    )
    dispatch_result = dispatch_execution_batch(
        run_dir=Path(args.run_dir),
        mode=args.mode,
        spec_path=args.spec,
        task_graph_path=args.task_graph,
        out_path=Path(args.out) if args.out else None,
    )
    return {"status": "pass", "init": init_result, "dispatch": dispatch_result}


def command_execution_next(args: argparse.Namespace) -> dict[str, Any]:
    task_states = read_all_task_states(Path(args.run_dir))
    decision = select_next_execution_task(task_states)
    plan = write_execution_plan(Path(args.run_dir), task_states)
    route = None
    if decision["status"] == "ready" and decision.get("task_id"):
        state = read_task_state(Path(args.run_dir), decision["task_id"])
        current_state = "IMPLEMENTING" if state["state"] == "TASK_READY" else state["state"]
        route = dict(EXECUTION_ROUTE_BY_STATE.get(current_state, {}))
        route["current_state"] = current_state
        if state["state"] == "TASK_READY":
            route["auto_event"] = "implementation-started"
    return {"status": decision["status"], "decision": decision, "route": route, "execution_plan": plan}


def command_execution_dispatch(args: argparse.Namespace) -> dict[str, Any]:
    return dispatch_next_execution_task(
        run_dir=Path(args.run_dir),
        mode=args.mode,
        spec_path=args.spec,
        task_graph_path=args.task_graph,
        out_path=Path(args.out) if args.out else None,
    )


def command_execution_dispatch_batch(args: argparse.Namespace) -> dict[str, Any]:
    return dispatch_execution_batch(
        run_dir=Path(args.run_dir),
        mode=args.mode,
        spec_path=args.spec,
        task_graph_path=args.task_graph,
        out_path=Path(args.out) if args.out else None,
    )


def command_task_event(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = Path(args.run_dir)
    state = read_task_state(run_dir, args.task_id)
    updated = apply_task_event(state, args.event, args.evidence, args.artifact)
    write_task_state(run_dir, updated)
    plan = write_execution_plan(run_dir, read_all_task_states(run_dir))
    return {
        "status": "pass",
        "task_id": args.task_id,
        "task_state": updated["state"],
        "task_status": updated["status"],
        "execution_status": plan["status"],
        "next_allowed_events": updated["next_allowed_events"],
    }


def command_execution_status(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = Path(args.run_dir)
    states = read_all_task_states(run_dir)
    plan = write_execution_plan(run_dir, states)
    return {"status": "pass", "execution_plan": plan}


def command_dry_run(args: argparse.Namespace) -> dict[str, Any]:
    return run_dry_run(Path(args.out))
