"""Argument parser and entry point."""
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

from .commands import *  # noqa: F401,F403


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lodestar local harness helpers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate Lodestar JSON artifacts")
    validate.add_argument(
        "kind",
        choices=[
            "locked-spec",
            "task-graph",
            "build-evidence",
            "review-report",
            "amendment-request",
            "final-handoff",
            "proof-bundle",
            "checklist-report",
            "browser-evidence",
            "quality-report",
            "debrief",
            "execution-plan",
            "task-state",
            "agent-dispatch",
            "agent-dispatch-batch",
            "responsive-matrix",
        ],
    )
    validate.add_argument("path")
    validate.add_argument("--spec", help="Locked Spec path for task coverage validation")
    validate.set_defaults(func=command_validate)

    runner = subparsers.add_parser("runner-step", help="Apply a Lodestar runner transition")
    runner.add_argument("--state", required=True)
    runner.add_argument("--event", required=True)
    runner.add_argument("--evidence", required=True)
    runner.add_argument("--out")
    runner.set_defaults(func=command_runner_step)

    negative = subparsers.add_parser("negative-checks", help="Run deterministic negative route checks")
    negative.add_argument("--skills-dir", default="skills")
    negative.set_defaults(func=command_negative_checks)

    upstream = subparsers.add_parser("upstream-check", help="Validate vendored upstream registry")
    upstream.add_argument("--root", default=".")
    upstream.add_argument("--map", help="Path to upstream-map.json")
    upstream.set_defaults(func=command_upstream_check)

    spec_gate = subparsers.add_parser("spec-gate", help="Run the Spec Kit based Lodestar spec gate adapter")
    spec_gate.add_argument("--spec", required=True, help="Locked Spec JSON path")
    spec_gate.add_argument("--out", required=True, help="Spec gate report JSON output path")
    spec_gate.add_argument("--ux-lock", help="UX lock markdown path")
    spec_gate.add_argument("--decision-log", help="Decision log JSONL path")
    spec_gate.add_argument("--report-only", action="store_true", help="Write the report but do not fail the command on gate failure")
    spec_gate.set_defaults(func=command_spec_gate)

    quality_gate = subparsers.add_parser("quality-gate", help="Run the gstack/CE based Lodestar Quality/QA adapter")
    quality_gate.add_argument("--run-dir", required=True, help="Run directory containing Lodestar artifacts")
    quality_gate.add_argument("--out", required=True, help="Quality report JSON output path")
    quality_gate.add_argument("--run-id")
    quality_gate.add_argument("--spec", help="Locked Spec JSON path, default: run-dir/locked-spec.json")
    quality_gate.add_argument("--execution-plan", help="Execution plan JSON path, default: run-dir/execution-plan.json")
    quality_gate.add_argument("--build", help="Build evidence JSON path, default: run-dir/build-evidence.json")
    quality_gate.add_argument("--review", help="Review report JSON path, default: run-dir/review-report.json")
    quality_gate.add_argument("--ux-lock", help="UX lock markdown path, default: run-dir/shape-lock.md")
    quality_gate.add_argument("--proof-bundle", help="Proof bundle JSON path, default: run-dir/proof-bundle.json")
    quality_gate.add_argument("--browser-evidence", help="Browser evidence JSON path, default: run-dir/browser-evidence.json when present")
    quality_gate.add_argument("--report-only", action="store_true", help="Write the report but do not fail the command on gate failure")
    quality_gate.set_defaults(func=command_quality_gate)

    browser_collect = subparsers.add_parser("browser-collect", help="Collect browser QA evidence from a URL, HTML artifact, or rendered browser snapshot")
    browser_collect.add_argument("--out", required=True, help="Browser evidence JSON output path")
    browser_collect.add_argument("--run-id")
    browser_collect.add_argument("--url", help="HTTP URL to collect")
    browser_collect.add_argument("--html", help="HTML file to collect deterministically")
    browser_collect.add_argument("--snapshot", help="Rendered browser snapshot JSON from Playwright, Codex Browser, or another browser tool")
    browser_collect.add_argument("--expect-text", action="append", help="Text that must appear in the target page")
    browser_collect.add_argument("--viewport", choices=sorted(BROWSER_VIEWPORTS), default="desktop")
    browser_collect.add_argument("--screenshot", help="Optional screenshot artifact path produced by a browser tool")
    browser_collect.add_argument("--console-errors", help="Optional JSON or text file containing browser console errors")
    browser_collect.add_argument("--timeout", type=int, default=10)
    browser_collect.add_argument("--report-only", action="store_true", help="Write failing evidence without failing the command")
    browser_collect.set_defaults(func=command_browser_collect)

    responsive_matrix = subparsers.add_parser("responsive-matrix", help="Aggregate mobile, tablet, and desktop browser evidence")
    responsive_matrix.add_argument("--out", required=True, help="Responsive matrix JSON output path")
    responsive_matrix.add_argument("--run-id")
    responsive_matrix.add_argument("--mobile", required=True, help="Mobile browser-evidence JSON path")
    responsive_matrix.add_argument("--tablet", required=True, help="Tablet browser-evidence JSON path")
    responsive_matrix.add_argument("--desktop", required=True, help="Desktop browser-evidence JSON path")
    responsive_matrix.add_argument("--require-screenshots", action="store_true", help="Fail unless each viewport evidence contains a screenshot artifact")
    responsive_matrix.add_argument("--report-only", action="store_true", help="Write failing matrix without failing the command")
    responsive_matrix.set_defaults(func=command_responsive_matrix)

    design_gate = subparsers.add_parser("design-gate", help="Validate DESIGN.md against the release-quality rubric")
    design_gate.add_argument("--design", required=True, help="DESIGN.md path")
    design_gate.add_argument("--shape", help="Optional final shape.html path")
    design_gate.add_argument("--visual-qa", help="Optional visual-qa.md path")
    design_gate.add_argument("--responsive-matrix", help="Optional responsive-matrix.json path")
    design_gate.add_argument("--require-visual-qa", action="store_true", help="Fail unless visual QA evidence records a pass")
    design_gate.add_argument("--require-responsive-matrix", action="store_true", help="Fail unless mobile/tablet/desktop responsive evidence passes")
    design_gate.add_argument("--report-only", action="store_true", help="Print failing findings without failing the command")
    design_gate.set_defaults(func=command_design_gate)

    ce_synthesize = subparsers.add_parser("ce-synthesize", help="Synthesize repeated failure evidence into a CE fix brief")
    ce_synthesize.add_argument("--run-dir", required=True, help="Run directory containing Lodestar artifacts")
    ce_synthesize.add_argument("--out", required=True, help="CE synthesis JSON output path")
    ce_synthesize.add_argument("--brief-out", help="CE brief markdown output path")
    ce_synthesize.add_argument("--run-id")
    ce_synthesize.add_argument("--spec", help="Locked Spec JSON path, default: run-dir/locked-spec.json")
    ce_synthesize.add_argument("--execution-plan", help="Execution plan JSON path, default: run-dir/execution-plan.json")
    ce_synthesize.add_argument("--review", help="Review report JSON path, default: run-dir/review-report.json")
    ce_synthesize.add_argument("--quality", help="Quality report JSON path, default: run-dir/quality-report.json")
    ce_synthesize.add_argument("--build", help="Build evidence JSON path, default: run-dir/build-evidence.json")
    ce_synthesize.add_argument("--report-only", action="store_true", help="Write blocked reports without failing the command")
    ce_synthesize.set_defaults(func=command_ce_synthesize)

    init = subparsers.add_parser("init-run", help="Initialize a completeness-first Lodestar run record")
    init.add_argument("--root", default=".")
    init.add_argument("--run-id")
    init.add_argument("--out", help="Override run directory")
    init.set_defaults(func=command_init_run)

    advisor = subparsers.add_parser("advisor", help="Resolve advisor routing with Claude/Codex fallback")
    advisor.add_argument("--issue", default="")
    advisor.add_argument("--issue-file")
    advisor.add_argument("--simulate", choices=["claude-available", "claude-limit", "codex-second-pass"])
    advisor.set_defaults(func=command_advisor)

    worktree = subparsers.add_parser("worktree-plan", help="Create a Git worktree plan for task graph")
    worktree.add_argument("task_graph")
    worktree.add_argument("--repo", default=".")
    worktree.add_argument("--worktrees", default=".lodestar/worktrees")
    worktree.add_argument("--out")
    worktree.add_argument("--ensure-repo", action="store_true")
    worktree.add_argument("--create", action="store_true")
    worktree.set_defaults(func=command_worktree_plan)

    execution_init = subparsers.add_parser("execution-init", help="Initialize task execution records from a task graph")
    execution_init.add_argument("--task-graph", required=True)
    execution_init.add_argument("--spec", required=True)
    execution_init.add_argument("--run-dir", required=True)
    execution_init.add_argument("--run-id")
    execution_init.add_argument("--repo", default=".")
    execution_init.add_argument("--worktrees", default=".lodestar/worktrees")
    execution_init.set_defaults(func=command_execution_init)

    execution_start = subparsers.add_parser(
        "execution-start",
        help="Initialize execution records and immediately dispatch all dependency-unblocked agent tasks",
    )
    execution_start.add_argument("--task-graph", required=True)
    execution_start.add_argument("--spec", required=True)
    execution_start.add_argument("--run-dir", required=True)
    execution_start.add_argument("--run-id")
    execution_start.add_argument("--repo", default=".")
    execution_start.add_argument("--worktrees", default=".lodestar/worktrees")
    execution_start.add_argument("--mode", choices=sorted(EXECUTION_DISPATCH_MODES), default="single-agent-fallback")
    execution_start.add_argument("--out")
    execution_start.set_defaults(func=command_execution_start)

    execution_next = subparsers.add_parser("execution-next", help="Show the next dependency-unblocked execution route")
    execution_next.add_argument("--run-dir", required=True)
    execution_next.set_defaults(func=command_execution_next)

    execution_dispatch = subparsers.add_parser(
        "execution-dispatch",
        help="Dispatch the next runnable task to the proper Lodestar role and write agent-dispatch.json",
    )
    execution_dispatch.add_argument("--run-dir", required=True)
    execution_dispatch.add_argument("--spec", required=True)
    execution_dispatch.add_argument("--task-graph", required=True)
    execution_dispatch.add_argument("--mode", choices=sorted(EXECUTION_DISPATCH_MODES), default="single-agent-fallback")
    execution_dispatch.add_argument("--out")
    execution_dispatch.set_defaults(func=command_execution_dispatch)

    execution_dispatch_batch = subparsers.add_parser(
        "execution-dispatch-batch",
        help="Dispatch all dependency-unblocked and active execution-loop tasks as a max-parallel batch",
    )
    execution_dispatch_batch.add_argument("--run-dir", required=True)
    execution_dispatch_batch.add_argument("--spec", required=True)
    execution_dispatch_batch.add_argument("--task-graph", required=True)
    execution_dispatch_batch.add_argument("--mode", choices=sorted(EXECUTION_DISPATCH_MODES), default="single-agent-fallback")
    execution_dispatch_batch.add_argument("--out")
    execution_dispatch_batch.set_defaults(func=command_execution_dispatch_batch)

    task_event = subparsers.add_parser("task-event", help="Apply a per-task execution loop event")
    task_event.add_argument("--run-dir", required=True)
    task_event.add_argument("--task-id", required=True)
    task_event.add_argument("--event", required=True)
    task_event.add_argument("--evidence", required=True)
    task_event.add_argument("--artifact")
    task_event.set_defaults(func=command_task_event)

    execution_status = subparsers.add_parser("execution-status", help="Refresh and print execution plan status")
    execution_status.add_argument("--run-dir", required=True)
    execution_status.set_defaults(func=command_execution_status)

    dry_run = subparsers.add_parser("dry-run", help="Run a deterministic Lodestar full-skill dry-run")
    dry_run.add_argument("--out", default=".lodestar/dry-run")
    dry_run.set_defaults(func=command_dry_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
    except LodestarError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
