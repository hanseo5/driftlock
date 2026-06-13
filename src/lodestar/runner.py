"""Run record and runner state machine: init, transitions, advisor routing."""
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

from .validators import *  # noqa: F401,F403


def new_runner_state() -> dict[str, Any]:
    return {"runner_state": "INTAKE", "history": []}


def new_proof_bundle(run_id: str, status: str = "in-progress") -> dict[str, Any]:
    gate_status = "pass" if status == "pass" else "pending"
    return {
        "run_id": run_id,
        "status": status,
        "gates": {gate: gate_status for gate in PROOF_BUNDLE_GATES},
        "artifacts": {},
        "summary": "Proof bundle initialized." if status != "pass" else "All proof bundle gates passed.",
    }


def read_upstream_map(root: Path, map_path: str | None = None) -> dict[str, Any]:
    path = Path(map_path) if map_path else root / "references" / "upstream-map.json"
    if not path.is_absolute():
        path = root / path
    upstream_map = read_json(path)
    fail_if_errors(validate_upstream_map_obj(upstream_map, root))
    return upstream_map


def init_run(root: Path, run_id: str | None = None, out_dir: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    upstream_map = read_upstream_map(root)
    resolved_run_id = run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    run_dir = Path(out_dir) if out_dir else root / ".lodestar" / "runs" / resolved_run_id
    if not run_dir.is_absolute():
        run_dir = root / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)

    state = new_runner_state()
    state.update(
        {
            "run_id": resolved_run_id,
            "strategy": "completeness-first",
            "created_at": utc_now(),
            "upstream_sources": [
                {
                    "id": repo["id"],
                    "commit": repo["commit"],
                    "vendored_root": repo["vendored_root"],
                    "layers": repo["lodestar_layers"],
                }
                for repo in upstream_map["repositories"]
            ],
            "proof_bundle": new_proof_bundle(resolved_run_id),
            "artifacts": {},
        }
    )
    write_json(run_dir / "state.json", state)
    write_json(run_dir / "proof-bundle.json", state["proof_bundle"])
    write_json(
        run_dir / "upstream-sources.json",
        {
            "run_id": resolved_run_id,
            "strategy": "completeness-first",
            "repositories": upstream_map["repositories"],
        },
    )
    return {"status": "pass", "run_id": resolved_run_id, "run_dir": str(run_dir), "state": state}


def apply_runner_event(state: dict[str, Any], event: str, evidence: str) -> dict[str, Any]:
    current = state.get("runner_state", "INTAKE")
    if current not in RUNNER_STATES:
        raise LodestarError(f"Unknown runner state: {current}")
    key = (current, event)
    if key not in RUNNER_TRANSITIONS:
        raise LodestarError(f"Invalid runner transition: {current} + {event}")
    next_state = RUNNER_TRANSITIONS[key]
    updated = dict(state)
    updated["runner_state"] = next_state
    updated.setdefault("history", [])
    updated["history"].append({"at": utc_now(), "event": event, "from": current, "to": next_state, "evidence": evidence})
    return updated


def advisor_route(issue: str, simulate: str | None = None) -> dict[str, Any]:
    if simulate == "claude-available":
        primary = "claude"
        status = "available"
        fallback = "not-used"
    elif simulate == "claude-limit":
        primary = "claude"
        status = "limit-or-unavailable"
        fallback = "codex-second-pass"
    elif simulate == "codex-second-pass":
        primary = "codex"
        status = "available"
        fallback = "local-evidence"
    else:
        claude = shutil.which("claude")
        codex = shutil.which("codex")
        if claude:
            primary, status, fallback = "claude", "available", "codex-second-pass" if codex else "local-evidence"
        elif codex:
            primary, status, fallback = "codex", "available", "local-evidence"
        else:
            primary, status, fallback = "local-evidence", "no-model-cli-found", "needs-user"
    return {
        "issue": issue,
        "primary": primary,
        "primary_status": status,
        "fallback": fallback,
        "advisor_confidence": "medium" if primary != "local-evidence" else "low",
        "requires_user_approval": True,
        "auto_approved": False,
        "recommendation": "Translate advisor output into product options; never auto-approve product intent.",
    }
