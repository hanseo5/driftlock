"""Deterministic dry-run plus the fake artifacts it exercises."""
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
from .execution import *  # noqa: F401,F403


def fake_locked_spec() -> dict[str, Any]:
    return {
        "id": "dryrun-spec",
        "title": "Full-Skill Lodestar Dry Run",
        "status": "locked",
        "intent": "Build a local harness flow that proves Lodestar has separate first-class skills before implementation.",
        "product_shape": {
            "primary_user": "A non-developer product owner delegating long-horizon development to AI agents.",
            "first_screen": "A wireframe preview, design-system approval, and final UI/UX preview before implementation.",
            "core_flow": "Office Hours to wireframe approval to design-system approval to final UI/UX approval to Product Lock to gated execution.",
            "ux_principles": [
                "Show wireframe and final UI/UX previews before locking the spec.",
                "Interrupt the user only for product-impacting decisions.",
                "Prevent UX drift unless an amendment is approved.",
            ],
            "approved_preview": True,
            "approval_source": "dry-run-user-approval",
        },
        "goals": ["Prove that all 20 first-class skills appear in the dry-run trace."],
        "non_goals": ["Do not create a large orchestrator or MCP server in v0."],
        "success_criteria": [
            {"id": "SC1", "statement": "All 20 first-class skills are represented by the harness trace.", "testable": True},
            {"id": "SC2", "statement": "Final handoff happens only after UX guard, build, review, amendment, and integration pass.", "testable": True},
        ],
        "acceptance_scenarios": [
            {
                "id": "AS1",
                "given": "The user has approved the wireframe, design system, and final UI/UX preview.",
                "when": "The product is locked.",
                "then": "The Locked Spec contains product-shape evidence and all gates pass.",
            },
            {
                "id": "AS2",
                "given": "Review rejects a task and CE is activated.",
                "when": "CE creates a fix brief.",
                "then": "The route returns to fixer before builder and reviewer.",
            },
        ],
        "decisions": [
            {
                "id": "D1",
                "question": "Should old coarse skills remain?",
                "answer": "No. Replace them with first-class stage and role skills.",
                "source": "user-plan",
            },
            {
                "id": "D2",
                "question": "Can amendment advisors approve product intent?",
                "answer": "No. They advise; the user approves.",
                "source": "user-plan",
            },
        ],
        "decision_policy": [
            {"class": "mechanical", "owner": "harness", "default_action": "auto-resolve with evidence"},
            {"class": "taste", "owner": "user", "default_action": "show recommendation and request approval"},
            {"class": "user-challenge", "owner": "user", "default_action": "translate into product options"},
            {"class": "safety-destructive", "owner": "user", "default_action": "require explicit approval"},
        ],
        "gate_evidence": {
            "office_hours_gate": "pass",
            "brainstorm_gate": "pass",
            "grill_gate": "pass",
            "intent_brief_gate": "pass",
            "decision_policy_gate": "pass",
            "ux_preview_gate": "pass",
            "ux_approval_gate": "pass",
            "spec_gate": "pass",
            "analyze_gate": "pass",
        },
        "spec_evidence": {
            "data_model": {
                "status": "not_applicable",
                "reason": "Dry-run harness proof does not introduce durable product data entities.",
            },
            "non_functional_quality": [
                "Deterministic local validation must produce repeatable pass/fail evidence.",
                "The runner must reject invalid phase transitions.",
            ],
            "integrations": {
                "status": "not_applicable",
                "reason": "Dry-run does not call external services.",
            },
            "edge_failure": [
                "Build failure routes to fixer.",
                "Review rejection routes through debrief before returning to fixer.",
                "Spec conflict routes to amendment advisor with user approval required.",
            ],
            "constraints_tradeoffs": [
                "Vendored upstream files remain reference material, not directly exposed plugin skills.",
                "Completeness is prioritized over a tiny runner.",
            ],
            "terminology": [
                "Locked Spec",
                "UX lock",
                "spec gate",
                "proof bundle",
            ],
        },
    }


def fake_task_graph() -> dict[str, Any]:
    return {
        "spec_id": "dryrun-spec",
        "status": "ready",
        "tasks": [
            {
                "id": "T1",
                "title": "Implement full-skill runner state",
                "branch": "task/full-skill-runner-state",
                "role": "implementer",
                "acceptance_criteria": ["SC1 and AS1 are covered by trace evidence."],
                "covers": ["SC1", "AS1"],
                "dependencies": [],
                "parallel_group": "foundation",
                "write_scope": ["scripts/lodestar.py", "templates"],
                "merge_risk": "medium",
            },
            {
                "id": "T2",
                "title": "Finalize gated handoff",
                "branch": "task/final-gated-handoff",
                "role": "fixer",
                "acceptance_criteria": ["SC2 and AS2 are covered after simulated failure recovery."],
                "covers": ["SC2", "AS2"],
                "dependencies": ["T1"],
                "parallel_group": "delivery",
                "write_scope": ["templates/final-handoff.json", "templates/proof-bundle.json"],
                "merge_risk": "low",
            },
        ],
    }


def fake_build_evidence(status: str = "pass") -> dict[str, Any]:
    return {
        "task_id": "T2",
        "status": status,
        "commands": [{"cmd": "lodestar dry-run build simulation", "status": status}],
        "summary": "Build evidence generated by deterministic dry-run.",
    }


def fake_review_report(status: str = "approved") -> dict[str, Any]:
    approved = status == "approved"
    return {
        "task_id": "T2",
        "status": status,
        "reviewer_read_only": True,
        "code_edits_made": False,
        "review_stages": [
            {
                "stage": "spec-compliance-review",
                "status": "approved" if approved else "rejected",
                "summary": "Spec compliance review passed." if approved else "Spec compliance review found a simulated gap.",
            },
            {
                "stage": "code-quality-review",
                "status": "approved",
                "summary": "Code quality review passed.",
            },
        ],
        "findings": []
        if approved
        else [
            {
                "severity": "P1",
                "category": "repeat-failure",
                "summary": "Route needs CE before another blind retry.",
                "evidence": "Simulated review rejection in dry-run trace.",
                "owner": "debrief",
                "requires_verification": True,
            }
        ],
    }


def fake_amendment_request() -> dict[str, Any]:
    return {
        "id": "AR1",
        "class": "clarification",
        "requires_user_approval": True,
        "auto_approved": False,
        "advisor": advisor_route("Dry-run amendment conflict.", "claude-limit"),
        "options": ["Keep locked spec", "Approve amendment", "Defer to non-goal"],
    }


def fake_final_handoff() -> dict[str, Any]:
    return {
        "id": "FH1",
        "status": "pass",
        "summary": "Final handoff produced only after all first-class skills and gates passed.",
        "gates": {
            "ux_guard": "pass",
            "build": "pass",
            "review": "pass",
            "amendment": "pass",
            "integration": "pass",
            "qa": "pass",
            "proof": "pass",
        },
        "evidence": [
            "20 skills represented in dry-run trace",
            "UX approval present before product lock",
            "CE returned to fixer before builder/reviewer",
            "Amendment request required user approval",
            "Quality report passed",
            "CE synthesis returned to fixer, not reviewer or handoff",
        ],
        "artifacts": {
            "proof_bundle": "proof-bundle.json",
            "quality_report": "quality-report.json",
        },
        "next_action": "Deliver result.",
    }


def fake_done_execution_plan() -> dict[str, Any]:
    task_states = []
    for task in fake_task_graph()["tasks"]:
        state = new_task_state(task, "dry-run", "dryrun-spec", Path(".lodestar/worktrees") / task["id"])
        for event in ("implementation-started", "implementation-ready", "build-pass", "reviewer-approve", "merge-pass"):
            state = apply_task_event(state, event, f"{task['id']} {event}")
        task_states.append(state)
    return build_execution_plan("dry-run", "dryrun-spec", Path(".lodestar/dry-run"), task_states)


def run_dry_run(out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    # The dry-run reads the repo's references/ and third_party/, so resolve the
    # root from the working directory (run it from a Lodestar checkout).
    root = Path.cwd()
    upstream_map = read_upstream_map(root)
    spec = fake_locked_spec()
    task_graph = fake_task_graph()
    build_evidence = fake_build_evidence("pass")
    rejected_review = fake_review_report("rejected")
    approved_review = fake_review_report("approved")
    amendment_request = fake_amendment_request()
    final_handoff = fake_final_handoff()
    ux_preview_html = "<!doctype html><html lang=\"en\"><title>Lodestar Shape</title><h1>UX Preview Approved</h1></html>\n"
    browser_evidence = build_browser_evidence(
        run_id="dry-run",
        mode="html",
        source="shape.html",
        html_text=ux_preview_html,
        expected_text=["UX Preview Approved"],
        viewport_name="desktop",
    )
    browser_evidence["_path"] = "browser-evidence.json"
    mobile_browser_evidence = build_browser_evidence(
        run_id="dry-run",
        mode="html",
        source="shape.html",
        html_text=ux_preview_html,
        expected_text=["UX Preview Approved"],
        viewport_name="mobile",
    )
    mobile_browser_evidence["_path"] = "browser-evidence-mobile.json"
    tablet_browser_evidence = build_browser_evidence(
        run_id="dry-run",
        mode="html",
        source="shape.html",
        html_text=ux_preview_html,
        expected_text=["UX Preview Approved"],
        viewport_name="tablet",
    )
    tablet_browser_evidence["_path"] = "browser-evidence-tablet.json"
    responsive_matrix = build_responsive_matrix(
        "dry-run",
        {
            "mobile": mobile_browser_evidence,
            "tablet": tablet_browser_evidence,
            "desktop": browser_evidence,
        },
    )
    fail_if_errors(validate_responsive_matrix_obj(responsive_matrix))
    proof_bundle = new_proof_bundle("dry-run", "pass")
    proof_bundle["artifacts"] = {
        "locked_spec": "locked-spec.json",
        "task_graph": "task-graph.json",
        "execution_plan": "execution-plan.json",
        "ux_guard": "shape-lock.md",
        "build_evidence": "build-evidence.json",
        "review_report": "review-report.json",
        "amendment_request": "amendment-request.json",
        "quality_report": "quality-report.json",
        "browser_evidence": "browser-evidence.json",
        "responsive_matrix": "responsive-matrix.json",
        "proof_bundle": "proof-bundle.json",
        "debrief": "debrief.json",
        "debrief_brief": "debrief-brief.md",
        "final_handoff": "final-handoff.json",
    }
    proof_bundle["summary"] = "Dry-run proof bundle passed all completeness-first gates."

    fail_if_errors(validate_locked_spec_obj(spec))
    fail_if_errors(validate_task_graph_obj(task_graph, spec))
    fail_if_errors(validate_build_evidence_obj(build_evidence))
    fail_if_errors(validate_review_report_obj(rejected_review))
    fail_if_errors(validate_review_report_obj(approved_review))
    fail_if_errors(validate_amendment_request_obj(amendment_request))
    fail_if_errors(validate_browser_evidence_obj(browser_evidence))
    fail_if_errors(validate_final_handoff_obj(final_handoff))
    fail_if_errors(validate_proof_bundle_obj(proof_bundle))

    trace = [
        {"skill": "lodestar-survey", "phase": "office-hours", "gate": "pass"},
        {"skill": "lodestar-scout", "phase": "brainstorm", "gate": "pass"},
        {"skill": "lodestar-shakedown", "phase": "grill", "gate": "pass"},
        {"skill": "lodestar-manifest", "phase": "intent-brief", "gate": "pass"},
        {"skill": "lodestar-triage", "phase": "decision-classify", "gate": "pass"},
        {"skill": "lodestar-call", "phase": "decision-card", "gate": "pass"},
        {"skill": "lodestar-shape", "phase": "ux-preview", "gate": "pass", "artifact": "wireframe.html"},
        {"skill": "lodestar-palette", "phase": "design-system", "gate": "pass", "artifact": "DESIGN.md"},
        {"skill": "lodestar-shape", "phase": "ux-preview", "gate": "pass", "artifact": "shape.html"},
        {"skill": "lodestar-shape-lock", "phase": "ux-approval", "gate": "pass"},
        {"skill": "lodestar-lock", "phase": "product-lock", "gate": "pass"},
        {"skill": "lodestar-checklist", "phase": "spec-gate", "gate": "pass"},
        {"skill": "lodestar-stages", "phase": "task-split", "gate": "pass"},
        {"skill": "lodestar-engineer", "phase": "implementer", "gate": "pass"},
        {"skill": "lodestar-integrator", "phase": "builder", "gate": "fail", "route": "fixer"},
        {"skill": "lodestar-eva", "phase": "fixer", "gate": "pass", "route": "builder"},
        {"skill": "lodestar-integrator", "phase": "builder", "gate": "pass", "route": "reviewer"},
        {"skill": "lodestar-flight-control", "phase": "reviewer", "gate": "fail", "route": "debrief"},
        {"skill": "lodestar-debrief", "phase": "debrief", "gate": "pass", "route": "fixer"},
        {"skill": "lodestar-eva", "phase": "fixer", "gate": "pass", "route": "builder"},
        {"skill": "lodestar-integrator", "phase": "builder", "gate": "pass", "route": "reviewer"},
        {"skill": "lodestar-flight-control", "phase": "reviewer", "gate": "pass", "route": "merge"},
        {"skill": "lodestar-integrator", "phase": "merge", "gate": "pass", "route": "ux-guard"},
        {"skill": "lodestar-guard", "phase": "ux-guard", "gate": "pass"},
        {"skill": "lodestar-course-correct", "phase": "amend-advisor", "gate": "needs-user"},
        {"skill": "lodestar-dock", "phase": "quality-gate", "gate": "pass", "route": "proof"},
        {"skill": "lodestar-dock", "phase": "proof-bundle", "gate": "pass", "route": "handoff"},
        {"skill": "lodestar-dock", "phase": "handoff", "gate": "pass"},
    ]
    trace_skills = {step["skill"] for step in trace}
    missing_trace_skills = sorted(set(SKILLS) - trace_skills)
    if missing_trace_skills:
        raise LodestarError(f"Dry-run trace missing skills: {', '.join(missing_trace_skills)}")

    write_text(out_dir / "survey.md", "# Office Hours\n\nDry-run office hours completed.\n")
    write_text(out_dir / "scout-notes.md", "# Brainstorm Notes\n\nDry-run options explored.\n")
    write_text(out_dir / "manifest.md", "# Intent Brief\n\nDry-run intent brief completed.\n")
    write_json(out_dir / "call.json", {"id": "DC1", "recommended": "Approve wireframe, DESIGN.md, then final UI/UX preview", "requires_user": True})
    write_text(out_dir / "wireframe.html", ux_preview_html.replace("Lodestar Shape", "Lodestar Wireframe"))
    write_text(
        out_dir / "DESIGN.md",
        "# DESIGN.md\n\n"
        "## Product Archetype\n\nOperational SaaS web app.\n\n"
        "## Benchmark Bar\n\n"
        "- Linear: compact work-surface density and restrained navigation.\n"
        "- Stripe Dashboard: financial hierarchy, table clarity, and semantic status.\n\n"
        "## Visual Theme\n\nCompact, operational, evidence-first.\n\n"
        "## Color Palette\n\nUse semantic roles for surface, ink, accent, warning, danger, and success.\n\n"
        "## Typography\n\nUse a compact system UI hierarchy with readable table text.\n\n"
        "## Component Inventory\n\nNavigation, KPI cards, data table, detail pane, primary actions, empty/loading/error states.\n\n"
        "## Layout Principles\n\nFirst screen must reveal status, priority, and next action without scrolling.\n\n"
        "## Data Realism\n\nUse domain-specific sample data, varied statuses, realistic metrics, and no placeholder copy.\n\n"
        "## Release-Quality Acceptance Criteria\n\n"
        "- First-screen decision speed: pass within 3 seconds.\n"
        "- Benchmark fit: match the named references' density and hierarchy.\n"
        "- Component fidelity: controls, tables, states, and spacing must look production-ready.\n"
        "- Visual craft: no overlap, clipping, awkward wrapping, or random decoration.\n"
        "- No MVP tells: no wireframe labels, placeholder text, or generic hero slogans.\n\n"
        "## Visual QA Checklist\n\nCapture mobile, tablet, and desktop screenshots; inspect failures; record fixes; and require result: pass.\n\n"
        "## Do's\n\nPreserve approved structure and make the next action obvious.\n\n"
        "## Don'ts\n\nDo not ship generic card dashboards, placeholder data, or MVP-looking previews.\n\n"
        "## Responsive Behavior\n\n"
        "Mobile, tablet, and desktop must pass as a viewport matrix. Support 320 CSS px reflow. Use component adaptation and container-level rules before page-level breakpoints.\n\n"
        "## Agent Prompt Guide\n\nUse this design system as the source of truth.\n\nApproved by: dry-run\n",
    )
    write_text(out_dir / "design-preview.html", "<!doctype html><title>Design Preview</title><h1>Design Preview</h1>")
    write_text(out_dir / "palette.md", "# Design System Compatibility Summary\n\nSource of truth: DESIGN.md\n\nApproved by: dry-run\n")
    write_text(out_dir / "shape.html", ux_preview_html)
    write_text(
        out_dir / "visual-qa.md",
        "# Visual QA\n\nScreenshots: mobile, tablet, desktop dry-run evidence.\n\nFailures: none after dry-run inspection.\n\nFixes: none required.\n\nMobile: pass.\nTablet: pass.\nDesktop: pass.\n\nResult: pass\n",
    )
    write_text(out_dir / "shape-lock.md", "# UX Lock\n\nApproved wireframe: wireframe.html\nApproved design system: DESIGN.md\nApproved design preview: design-preview.html\nApproved final UI/UX preview: shape.html\nApproved visual QA: visual-qa.md\n")
    spec_gate_report = build_spec_gate_report(
        spec,
        "# UX Lock\n\nApproved wireframe: wireframe.html\nApproved design system: DESIGN.md\nApproved design preview: design-preview.html\nApproved final UI/UX preview: shape.html\nApproved visual QA: visual-qa.md\n\nApproved by: dry-run\n",
        [{"status": "accepted", "decision": "approved", "source": "dry-run"}],
    )
    fail_if_errors(validate_spec_gate_report_obj(spec_gate_report))
    write_json(out_dir / "locked-spec.json", spec)
    write_json(out_dir / "checklist-report.json", spec_gate_report)
    write_json(out_dir / "task-graph.json", task_graph)
    batch_smoke_graph = {
        "spec_id": "dryrun-spec",
        "status": "ready",
        "tasks": [
            {
                "id": "B1",
                "title": "Batch root one",
                "branch": "task/batch-root-one",
                "role": "implementer",
                "acceptance_criteria": ["SC1 and AS1 are covered by batch root one."],
                "covers": ["SC1", "AS1"],
                "dependencies": [],
                "parallel_group": "batch-root",
                "write_scope": ["Sources/BatchOne"],
                "merge_risk": "low",
            },
            {
                "id": "B2",
                "title": "Batch root two",
                "branch": "task/batch-root-two",
                "role": "implementer",
                "acceptance_criteria": ["SC2 and AS2 are covered by batch root two."],
                "covers": ["SC2", "AS2"],
                "dependencies": [],
                "parallel_group": "batch-root",
                "write_scope": ["Sources/BatchTwo"],
                "merge_risk": "low",
            },
        ],
    }
    batch_smoke_run = out_dir / "batch-smoke"
    init_execution_run(batch_smoke_graph, spec, batch_smoke_run, root, Path(".lodestar/worktrees"), "dry-run-batch")
    batch_smoke = dispatch_execution_batch(batch_smoke_run, "subagent", "locked-spec.json", "task-graph.json")
    fail_if_errors(validate_agent_dispatch_batch_obj(batch_smoke["batch"]))
    init_execution_run(task_graph, spec, out_dir, root, Path(".lodestar/worktrees"), "dry-run")
    for task_id, event, evidence in [
        ("T1", "implementation-started", "T1 implementer started."),
        ("T1", "implementation-ready", "T1 implementation handoff ready."),
        ("T1", "build-pass", "T1 build evidence passed."),
        ("T1", "reviewer-approve", "T1 review approved."),
        ("T1", "merge-pass", "T1 merge integrated."),
        ("T2", "implementation-started", "T2 implementer started."),
        ("T2", "implementation-ready", "T2 implementation handoff ready."),
        ("T2", "build-fail", "T2 build failed and routed to fixer."),
        ("T2", "fix-ready", "T2 fix ready for implementation loop."),
        ("T2", "implementation-ready", "T2 fix implementation ready."),
        ("T2", "build-pass", "T2 build passed after fix."),
        ("T2", "reviewer-reject", "T2 review rejected and routed to fixer."),
        ("T2", "ce-needed", "T2 repeated failure needs CE."),
        ("T2", "debrief-brief-ready", "T2 CE brief returned to fixer."),
        ("T2", "fix-ready", "T2 CE-informed fix ready."),
        ("T2", "implementation-ready", "T2 CE-informed implementation ready."),
        ("T2", "build-pass", "T2 final build passed."),
        ("T2", "reviewer-approve", "T2 final review approved."),
        ("T2", "merge-pass", "T2 merge integrated."),
    ]:
        state = read_task_state(out_dir, task_id)
        write_task_state(out_dir, apply_task_event(state, event, evidence))
    execution_plan = write_execution_plan(out_dir, read_all_task_states(out_dir))
    fail_if_errors(validate_execution_plan_obj(execution_plan))
    quality_report = build_quality_report(
        "dry-run",
        spec,
        execution_plan,
        build_evidence,
        approved_review,
        "# UX Lock\n\nApproved wireframe: wireframe.html\nApproved design system: DESIGN.md\nApproved design preview: design-preview.html\nApproved final UI/UX preview: shape.html\nApproved visual QA: visual-qa.md\n\nApproved by: dry-run\n",
        proof_bundle,
        browser_evidence,
        {
            "locked_spec": "locked-spec.json",
            "execution_plan": "execution-plan.json",
            "build_evidence": "build-evidence.json",
            "review_report": "review-report.json",
            "ux_lock": "shape-lock.md",
            "browser_evidence": "browser-evidence.json",
            "proof_bundle": "proof-bundle.json",
        },
    )
    fail_if_errors(validate_quality_report_obj(quality_report))
    debrief = build_debrief(
        "dry-run",
        spec,
        execution_plan,
        rejected_review,
        quality_report,
        build_evidence,
        {
            "review_report": "review-rejected-report.json",
            "quality_report": "quality-report.json",
            "execution_plan": "execution-plan.json",
            "build_evidence": "build-evidence.json",
        },
    )
    fail_if_errors(validate_debrief_obj(debrief))
    write_json(out_dir / "build-evidence.json", build_evidence)
    write_json(out_dir / "review-rejected-report.json", rejected_review)
    write_json(out_dir / "review-report.json", approved_review)
    write_json(out_dir / "browser-evidence-mobile.json", mobile_browser_evidence)
    write_json(out_dir / "browser-evidence-tablet.json", tablet_browser_evidence)
    write_json(out_dir / "browser-evidence.json", browser_evidence)
    write_json(out_dir / "responsive-matrix.json", responsive_matrix)
    write_json(out_dir / "quality-report.json", quality_report)
    write_json(out_dir / "debrief.json", debrief)
    write_text(out_dir / "debrief-brief.md", render_debrief_brief(debrief))
    write_json(out_dir / "amendment-request.json", amendment_request)
    write_json(out_dir / "final-handoff.json", final_handoff)
    write_json(out_dir / "proof-bundle.json", proof_bundle)
    write_json(
        out_dir / "upstream-sources.json",
        {
            "strategy": "completeness-first",
            "repository_count": len(upstream_map["repositories"]),
            "repositories": [
                {
                    "id": repo["id"],
                    "commit": repo["commit"],
                    "vendored_root": repo["vendored_root"],
                    "layers": repo["lodestar_layers"],
                }
                for repo in upstream_map["repositories"]
            ],
        },
    )
    write_json(
        out_dir / "state.json",
        {
            "run_id": "dry-run",
            "strategy": "completeness-first",
            "runner_state": "HANDOFF_READY",
            "upstream_sources": [repo["id"] for repo in upstream_map["repositories"]],
            "proof_bundle": proof_bundle,
            "history": trace,
        },
    )

    result = {
        "status": "pass",
        "out_dir": str(out_dir),
        "skill_count": len(SKILLS),
        "upstream_repository_count": len(upstream_map["repositories"]),
        "trace": trace,
        "final_handoff_after_all_gates": True,
        "proof_bundle_gates": list(PROOF_BUNDLE_GATES),
        "old_coarse_wrappers_removed": True,
        "artifacts": [
            "survey.md",
            "call.json",
            "wireframe.html",
            "DESIGN.md",
            "design-preview.html",
            "palette.md",
            "shape.html",
            "visual-qa.md",
            "shape-lock.md",
            "checklist-report.json",
            "task-graph.json",
            "execution-plan.json",
            "batch-smoke/dispatch/agent-dispatch-batch.json",
            "tasks/T1/state.json",
            "tasks/T2/state.json",
            "build-evidence.json",
            "review-rejected-report.json",
            "review-report.json",
            "browser-evidence-mobile.json",
            "browser-evidence-tablet.json",
            "browser-evidence.json",
            "responsive-matrix.json",
            "quality-report.json",
            "debrief.json",
            "amendment-request.json",
            "debrief-brief.md",
            "final-handoff.json",
            "proof-bundle.json",
            "upstream-sources.json",
            "state.json",
        ],
    }
    write_json(out_dir / "dry-run-summary.json", result)
    return result
