#!/usr/bin/env python3
"""Driftlock local harness helpers.

The harness stays intentionally small: Markdown skills carry agent behavior,
while this script validates the artifact contracts, applies runner transitions,
routes advisor fallback, plans Git worktrees, and runs a deterministic dry-run.
"""

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


SKILLS = (
    "driftlock-office-hours",
    "driftlock-brainstorm",
    "driftlock-grill",
    "driftlock-intent-brief",
    "driftlock-decision-classify",
    "driftlock-decision-card",
    "driftlock-design-system-lite",
    "driftlock-ux-preview",
    "driftlock-ux-approval",
    "driftlock-ux-guard",
    "driftlock-product-lock",
    "driftlock-spec-gate",
    "driftlock-task-split",
    "driftlock-implementer",
    "driftlock-builder",
    "driftlock-reviewer",
    "driftlock-fixer",
    "driftlock-amend-advisor",
    "driftlock-compound",
    "driftlock-handoff",
)

REMOVED_COARSE_SKILLS = {
    "driftlock-spec-lock",
    "driftlock-execute",
    "driftlock-amend",
}

PHASES = {
    "office-hours",
    "brainstorm",
    "grill",
    "intent-brief",
    "decision-classify",
    "decision-card",
    "design-system-lite",
    "ux-preview",
    "ux-approval",
    "ux-guard",
    "product-lock",
    "spec-gate",
    "task-split",
    "implementer",
    "builder",
    "reviewer",
    "fixer",
    "amend-advisor",
    "compound",
    "handoff",
}

STATUSES = {"pass", "fail", "blocked", "needs-user", "in-progress"}
CONFIDENCE = {"high", "medium", "low"}
DECISION_CLASSES = {"mechanical", "taste", "user-challenge", "safety-destructive"}
DECISION_OWNERS = {"harness", "user", "advisor"}
PRODUCT_LOCK_GATES = (
    "office_hours_gate",
    "brainstorm_gate",
    "grill_gate",
    "intent_brief_gate",
    "decision_policy_gate",
    "ux_preview_gate",
    "ux_approval_gate",
    "spec_gate",
    "analyze_gate",
)

PROOF_BUNDLE_GATES = (
    "ux_guard",
    "build",
    "review",
    "amendment",
    "integration",
    "qa",
    "proof",
)

UPSTREAM_LAYERS = {
    "office-hours-ui",
    "spec-engine",
    "execution-engine",
    "quality-engine",
    "compound-memory",
    "delivery-engine",
}

SPEC_GATE_CATEGORIES = (
    "functional_scope",
    "data_model",
    "ux_flow",
    "non_functional_quality",
    "integrations",
    "edge_failure",
    "constraints_tradeoffs",
    "terminology",
    "completion_signals",
    "placeholders",
)

SPEC_GATE_CATEGORY_LABELS = {
    "functional_scope": "Functional scope",
    "data_model": "Data model",
    "ux_flow": "UX flow",
    "non_functional_quality": "Non-functional quality",
    "integrations": "Integrations",
    "edge_failure": "Edge and failure handling",
    "constraints_tradeoffs": "Constraints and tradeoffs",
    "terminology": "Terminology",
    "completion_signals": "Completion signals",
    "placeholders": "Placeholders",
}

SPEC_GATE_STATUSES = {"pass", "fail", "not_applicable"}
SPEC_GATE_SEVERITIES = {"critical", "high", "medium", "low"}
SPEC_GATE_PLACEHOLDERS = (
    "TODO",
    "TBD",
    "NEEDS CLARIFICATION",
    "???",
    "<placeholder>",
    "[FEATURE NAME]",
    "[ARGUMENTS]",
)

QUALITY_CHECKS = (
    "execution_completion",
    "build_verification",
    "review_integrity",
    "ux_alignment",
    "acceptance_coverage",
    "regression_smoke",
    "integration_readiness",
    "accessibility_baseline",
    "proof_readiness",
)

QUALITY_CHECK_LABELS = {
    "execution_completion": "Execution completion",
    "build_verification": "Build verification",
    "review_integrity": "Review integrity",
    "ux_alignment": "UX alignment",
    "acceptance_coverage": "Acceptance coverage",
    "regression_smoke": "Regression smoke",
    "integration_readiness": "Integration readiness",
    "accessibility_baseline": "Accessibility baseline",
    "proof_readiness": "Proof readiness",
}

QUALITY_CHECK_STATUSES = {"pass", "fail", "warning", "not_applicable"}
QUALITY_SEVERITIES = {"critical", "high", "medium", "low"}
QUALITY_FAIL_SEVERITIES = {"critical", "high"}
QUALITY_REQUIRED_PASS_ARTIFACTS = {
    "ux_guard": "ux_guard",
    "build": "build_evidence",
    "review": "review_report",
    "qa": "quality_report",
    "browser_qa": "browser_evidence",
    "proof": "proof_bundle",
}

BROWSER_EVIDENCE_CHECKS = (
    "load",
    "title",
    "expected_text",
    "console",
    "accessibility_baseline",
    "responsive_baseline",
    "screenshot",
)

BROWSER_EVIDENCE_STATUSES = {"pass", "fail", "warning", "not_applicable"}
BROWSER_EVIDENCE_MODES = {"html", "url", "snapshot", "manual"}
BROWSER_VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "tablet": {"width": 834, "height": 1112},
    "mobile": {"width": 390, "height": 844},
}

CE_TRIGGER_KINDS = {
    "build_failure",
    "review_reject",
    "quality_failure",
    "review_integrity",
    "repeated_failure",
    "product_intent_conflict",
}
CE_SYNTHESIS_STATUSES = {"ready", "blocked"}
CE_RETURN_ROUTES = {"driftlock-fixer", "driftlock-implementer", "driftlock-amend-advisor"}
CE_FORBIDDEN_ROUTES = {"driftlock-reviewer", "driftlock-handoff"}
CE_LEARNING_STATUSES = {"required", "written", "not-needed"}

RUNNER_STATES = {
    "INTAKE",
    "OFFICE_HOURS_DONE",
    "BRAINSTORM_DONE",
    "GRILL_DONE",
    "INTENT_BRIEF_READY",
    "DECISION_CLASSIFIED",
    "DECISION_CARD_READY",
    "DESIGN_SYSTEM_READY",
    "UX_PREVIEW_READY",
    "UX_APPROVED",
    "PRODUCT_LOCKED",
    "SPEC_GATED",
    "TASK_SPLIT_READY",
    "IMPLEMENTING",
    "BUILDING",
    "REVIEWING",
    "MERGE_READY",
    "QA_READY",
    "PROOF_READY",
    "FIXING",
    "AMENDMENT_PENDING",
    "COMPOUNDING",
    "HANDOFF_READY",
}

RUNNER_TRANSITIONS = {
    ("INTAKE", "office-hours-pass"): "OFFICE_HOURS_DONE",
    ("OFFICE_HOURS_DONE", "brainstorm-pass"): "BRAINSTORM_DONE",
    ("BRAINSTORM_DONE", "grill-pass"): "GRILL_DONE",
    ("GRILL_DONE", "intent-brief-ready"): "INTENT_BRIEF_READY",
    ("INTENT_BRIEF_READY", "decision-classified"): "DECISION_CLASSIFIED",
    ("DECISION_CLASSIFIED", "decision-card-ready"): "DECISION_CARD_READY",
    ("DECISION_CARD_READY", "design-system-ready"): "DESIGN_SYSTEM_READY",
    ("DESIGN_SYSTEM_READY", "ux-preview-ready"): "UX_PREVIEW_READY",
    ("UX_PREVIEW_READY", "ux-approved"): "UX_APPROVED",
    ("UX_APPROVED", "product-locked"): "PRODUCT_LOCKED",
    ("PRODUCT_LOCKED", "spec-gate-pass"): "SPEC_GATED",
    ("SPEC_GATED", "task-split-ready"): "TASK_SPLIT_READY",
    ("TASK_SPLIT_READY", "implementation-started"): "IMPLEMENTING",
    ("IMPLEMENTING", "implementation-ready"): "BUILDING",
    ("BUILDING", "build-pass"): "REVIEWING",
    ("BUILDING", "build-fail"): "FIXING",
    ("REVIEWING", "reviewer-approve"): "MERGE_READY",
    ("REVIEWING", "reviewer-reject"): "FIXING",
    ("MERGE_READY", "merge-pass"): "QA_READY",
    ("MERGE_READY", "merge-conflict"): "FIXING",
    ("MERGE_READY", "ce-needed"): "COMPOUNDING",
    ("QA_READY", "quality-pass"): "PROOF_READY",
    ("QA_READY", "quality-fail"): "FIXING",
    ("QA_READY", "quality-ce-needed"): "COMPOUNDING",
    ("QA_READY", "amendment-needed"): "AMENDMENT_PENDING",
    ("PROOF_READY", "proof-pass"): "HANDOFF_READY",
    ("PROOF_READY", "proof-fail"): "FIXING",
    ("PROOF_READY", "ce-needed"): "COMPOUNDING",
    ("FIXING", "fix-ready"): "IMPLEMENTING",
    ("FIXING", "ce-needed"): "COMPOUNDING",
    ("COMPOUNDING", "ce-brief-ready"): "FIXING",
    ("FIXING", "amendment-needed"): "AMENDMENT_PENDING",
    ("AMENDMENT_PENDING", "amendment-approved"): "PRODUCT_LOCKED",
    ("HANDOFF_READY", "handoff-ready"): "HANDOFF_READY",
}

TASK_STATES = {
    "TASK_READY",
    "IMPLEMENTING",
    "BUILDING",
    "REVIEWING",
    "MERGE_READY",
    "FIXING",
    "COMPOUNDING",
    "AMENDMENT_PENDING",
    "TASK_DONE",
    "TASK_BLOCKED",
}

TASK_STATUSES = {"ready", "in-progress", "done", "blocked"}

TASK_TRANSITIONS = {
    ("TASK_READY", "implementation-started"): ("IMPLEMENTING", "in-progress", "implementation_attempts"),
    ("IMPLEMENTING", "implementation-ready"): ("BUILDING", "in-progress", None),
    ("IMPLEMENTING", "implementation-blocked"): ("TASK_BLOCKED", "blocked", None),
    ("BUILDING", "build-pass"): ("REVIEWING", "in-progress", "build_attempts"),
    ("BUILDING", "build-fail"): ("FIXING", "in-progress", "build_attempts"),
    ("REVIEWING", "reviewer-approve"): ("MERGE_READY", "in-progress", "review_attempts"),
    ("REVIEWING", "reviewer-reject"): ("FIXING", "in-progress", "review_attempts"),
    ("REVIEWING", "amendment-needed"): ("AMENDMENT_PENDING", "in-progress", None),
    ("MERGE_READY", "merge-pass"): ("TASK_DONE", "done", None),
    ("MERGE_READY", "merge-conflict"): ("FIXING", "in-progress", None),
    ("MERGE_READY", "ce-needed"): ("COMPOUNDING", "in-progress", "ce_cycles"),
    ("FIXING", "fix-ready"): ("IMPLEMENTING", "in-progress", "fix_attempts"),
    ("FIXING", "ce-needed"): ("COMPOUNDING", "in-progress", "ce_cycles"),
    ("FIXING", "amendment-needed"): ("AMENDMENT_PENDING", "in-progress", None),
    ("COMPOUNDING", "ce-brief-ready"): ("FIXING", "in-progress", None),
    ("AMENDMENT_PENDING", "amendment-approved"): ("IMPLEMENTING", "in-progress", None),
}

TASK_GATE_DEFAULTS = {
    "implementation": "pending",
    "build": "pending",
    "review": "pending",
    "merge": "pending",
    "ce": "not-needed",
    "amendment": "not-needed",
}

EXECUTION_DISPATCH_MODES = {"subagent", "single-agent-fallback"}
MERGE_RISKS = {"low", "medium", "high"}
REVIEW_STAGES = ("spec-compliance-review", "code-quality-review")
DISPATCHABLE_ACTIVE_STATES = {"IMPLEMENTING", "BUILDING", "REVIEWING", "MERGE_READY", "FIXING", "COMPOUNDING", "AMENDMENT_PENDING"}

EXECUTION_ROUTE_BY_STATE = {
    "IMPLEMENTING": {
        "role": "implementer",
        "skill": "driftlock-implementer",
        "mutates_code": True,
        "next_step": "make scoped code changes using TDD and produce implementation-handoff.json",
        "output_artifact": "implementation-handoff.json",
        "expected_events": ["implementation-ready", "implementation-blocked"],
    },
    "BUILDING": {
        "role": "builder",
        "skill": "driftlock-builder",
        "mutates_code": False,
        "next_step": "run build, lint, tests, smoke checks, and produce build-evidence.json",
        "output_artifact": "build-evidence.json",
        "expected_events": ["build-pass", "build-fail"],
    },
    "REVIEWING": {
        "role": "reviewer",
        "skill": "driftlock-reviewer",
        "mutates_code": False,
        "next_step": "perform two-stage read-only spec compliance and code quality review, then produce review-report.json",
        "output_artifact": "review-report.json",
        "expected_events": ["reviewer-approve", "reviewer-reject", "amendment-needed"],
        "review_stages": list(REVIEW_STAGES),
    },
    "MERGE_READY": {
        "role": "integrator",
        "skill": "driftlock-builder",
        "mutates_code": True,
        "next_step": "merge or integrate the reviewed task branch and produce merge-evidence.json",
        "output_artifact": "merge-evidence.json",
        "expected_events": ["merge-pass", "merge-conflict", "ce-needed"],
    },
    "FIXING": {
        "role": "fixer",
        "skill": "driftlock-fixer",
        "mutates_code": True,
        "next_step": "fix rejected or failed work and produce fix-handoff.json",
        "output_artifact": "fix-handoff.json",
        "expected_events": ["fix-ready", "ce-needed", "amendment-needed"],
    },
    "COMPOUNDING": {
        "role": "compound",
        "skill": "driftlock-compound",
        "mutates_code": False,
        "next_step": "synthesize repeated failure learning and route back to fixer or implementer",
        "output_artifact": "ce-synthesis.json",
        "expected_events": ["ce-brief-ready"],
    },
    "AMENDMENT_PENDING": {
        "role": "amend-advisor",
        "skill": "driftlock-amend-advisor",
        "mutates_code": False,
        "next_step": "advise on product-impacting amendment without auto-approving user intent",
        "output_artifact": "amendment-request.json",
        "expected_events": ["amendment-approved"],
    },
}


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


def attrs_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    return {key.lower(): value or "" for key, value in attrs}


class BrowserEvidenceHTMLParser(HTMLParser):
    """Extracts stable page signals without depending on a browser package."""

    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.text_chunks: list[str] = []
        self.heading_parts: list[str] = []
        self.heading_stack: list[str] = []
        self.button_stack: list[dict[str, Any]] = []
        self.input_attrs: list[dict[str, str]] = []
        self.label_for_ids: set[str] = set()
        self.html_lang = False
        self.links = 0
        self.buttons = 0
        self.buttons_without_name = 0
        self.inputs = 0
        self.inputs_without_label = 0
        self.images = 0
        self.images_without_alt = 0
        self.aria_labels = 0
        self._in_title = False
        self._suppressed_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        data = attrs_dict(attrs)
        if tag in {"script", "style", "noscript", "template"}:
            self._suppressed_depth += 1
            return
        if data.get("aria-label") or data.get("aria-labelledby"):
            self.aria_labels += 1
        if tag == "html" and non_empty_string(data.get("lang")):
            self.html_lang = True
        elif tag == "title":
            self._in_title = True
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.heading_stack.append(tag)
            self.heading_parts.append("")
        elif tag == "a":
            self.links += 1
        elif tag == "img":
            self.images += 1
            if data.get("aria-hidden") != "true" and data.get("role") != "presentation" and not non_empty_string(data.get("alt")):
                self.images_without_alt += 1
        elif tag == "input":
            input_type = data.get("type", "text").lower()
            if input_type not in {"hidden", "submit", "button", "reset"}:
                self.inputs += 1
                self.input_attrs.append(data)
        elif tag == "label":
            if non_empty_string(data.get("for")):
                self.label_for_ids.add(str(data["for"]))
        elif tag == "button":
            self.buttons += 1
            self.button_stack.append({"attrs": data, "text": []})

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "template"} and self._suppressed_depth:
            self._suppressed_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self.heading_stack:
            self.heading_stack.pop()
        elif tag == "button" and self.button_stack:
            button = self.button_stack.pop()
            attrs = button["attrs"]
            text = " ".join(button["text"]).strip()
            if not text and not attrs.get("aria-label") and not attrs.get("title"):
                self.buttons_without_name += 1

    def handle_data(self, data: str) -> None:
        if self._suppressed_depth:
            return
        stripped = " ".join(data.split())
        if not stripped:
            return
        if self._in_title:
            self.title_parts.append(stripped)
        else:
            self.text_chunks.append(stripped)
        if self.heading_stack and self.heading_parts:
            self.heading_parts[-1] = " ".join([self.heading_parts[-1], stripped]).strip()
        if self.button_stack:
            self.button_stack[-1]["text"].append(stripped)

    def close(self) -> None:
        super().close()
        for input_attr in self.input_attrs:
            input_id = input_attr.get("id")
            labelled = (
                non_empty_string(input_attr.get("aria-label"))
                or non_empty_string(input_attr.get("aria-labelledby"))
                or non_empty_string(input_attr.get("title"))
                or (non_empty_string(input_id) and str(input_id) in self.label_for_ids)
            )
            if not labelled:
                self.inputs_without_label += 1

    def page(self) -> dict[str, Any]:
        text = " ".join(self.text_chunks)
        headings = [heading for heading in self.heading_parts if heading.strip()]
        return {
            "title": " ".join(self.title_parts).strip(),
            "text_sample": text[:500],
            "_text_search": text,
            "text_length": len(text),
            "headings": headings[:12],
            "links": self.links,
            "buttons": self.buttons,
            "buttons_without_name": self.buttons_without_name,
            "inputs": self.inputs,
            "inputs_without_label": self.inputs_without_label,
            "images": self.images,
            "images_without_alt": self.images_without_alt,
            "aria_labels": self.aria_labels,
            "html_lang": self.html_lang,
        }


def require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(non_empty_string(item) for item in value)


def fail_if_errors(errors: list[str]) -> None:
    if errors:
        raise DriftlockError("\n".join(f"- {error}" for error in errors))


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
            "agent dispatch execution_policy.ce_forbidden_routes must match Driftlock CE constraints",
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
                finding.get("owner") in {"fixer", "compound", "amend-advisor", "human"},
                f"{prefix}.owner must be fixer, compound, amend-advisor, or human",
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
            layers = repo.get("driftlock_layers")
            require(errors, isinstance(layers, list) and bool(layers), f"{prefix}.driftlock_layers must be non-empty")
            if isinstance(layers, list):
                for layer in layers:
                    require(errors, layer in UPSTREAM_LAYERS, f"{prefix}.driftlock_layers has unknown layer: {layer}")
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
    require(errors, report.get("next_route") in SKILLS, "spec gate report next_route must be a Driftlock skill")

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
        require(errors, report.get("next_route") == "driftlock-task-split", "passing spec gate report must route to driftlock-task-split")
    if report.get("status") == "fail":
        require(errors, high_or_critical, "failing spec gate report must contain at least one critical/high finding")
        require(errors, report.get("next_route") != "driftlock-task-split", "failing spec gate report cannot route to driftlock-task-split")
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


def validate_quality_report_obj(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("run_id", "spec_id", "status", "upstream_source", "checks", "findings", "metrics", "next_route", "artifacts"):
        require(errors, key in report, f"quality report missing required field: {key}")
    require(errors, non_empty_string(report.get("run_id")), "quality report run_id must be non-empty")
    require(errors, non_empty_string(report.get("spec_id")), "quality report spec_id must be non-empty")
    require(errors, report.get("status") in {"pass", "fail"}, "quality report status must be pass or fail")
    require(errors, report.get("next_route") in SKILLS, "quality report next_route must be a Driftlock skill")

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
                finding_item.get("owner") in {"fixer", "compound", "amend-advisor", "handoff", "human"},
                f"{prefix}.owner must be fixer, compound, amend-advisor, handoff, or human",
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
        require(errors, report.get("next_route") == "driftlock-handoff", "passing quality report must route to driftlock-handoff")
    if report.get("status") == "fail":
        require(errors, high_or_critical, "failing quality report must contain at least one critical/high finding")
        require(errors, report.get("next_route") != "driftlock-handoff", "failing quality report cannot route to driftlock-handoff")
    return errors


def validate_ce_synthesis_obj(synthesis: dict[str, Any]) -> list[str]:
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
        if synthesis.get("return_route") == "driftlock-amend-advisor":
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


def finding(
    findings: list[dict[str, Any]],
    category: str,
    severity: str,
    summary: str,
    recommendation: str,
    source: str,
) -> None:
    findings.append(
        {
            "id": f"SG-{len(findings) + 1:03d}",
            "category": category,
            "severity": severity,
            "summary": summary,
            "recommendation": recommendation,
            "source": source,
        }
    )


def explicit_evidence(spec: dict[str, Any], key: str) -> Any:
    evidence = spec.get("spec_evidence")
    if isinstance(evidence, dict):
        return evidence.get(key)
    return None


def evidence_has_content(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value) and any(evidence_has_content(item) for item in value)
    if isinstance(value, dict):
        status = value.get("status")
        reason = value.get("reason")
        if status == "not_applicable" and non_empty_string(reason):
            return True
        return any(evidence_has_content(item) for item in value.values())
    return value is not None


def evidence_status(value: Any) -> str:
    if isinstance(value, dict) and value.get("status") == "not_applicable" and non_empty_string(value.get("reason")):
        return "not_applicable"
    if evidence_has_content(value):
        return "pass"
    return "fail"


def category_summary(status: str, pass_summary: str, fail_summary: str, na_summary: str | None = None) -> str:
    if status == "pass":
        return pass_summary
    if status == "not_applicable":
        return na_summary or pass_summary
    return fail_summary


def accepted_decision_count(decision_log: list[dict[str, Any]] | None) -> int:
    if not decision_log:
        return 0
    return sum(1 for item in decision_log if isinstance(item, dict) and item.get("status") == "accepted")


def read_decision_log(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise DriftlockError(f"Decision log not found: {path}") from exc
    entries: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise DriftlockError(f"Invalid JSONL in {path}:{line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise DriftlockError(f"Invalid decision log entry in {path}:{line_number}: expected object")
        entries.append(value)
    return entries


def read_optional_text(path: Path | None, label: str) -> str:
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise DriftlockError(f"{label} not found: {path}") from exc


def read_optional_json(path: Path | None, label: str) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        raise DriftlockError(f"{label} not found: {path}")
    return read_json(path)


def browser_finding(
    findings: list[dict[str, Any]],
    check: str,
    severity: str,
    summary: str,
    recommendation: str,
    source: str,
) -> None:
    findings.append(
        {
            "id": f"BR-{len(findings) + 1:03d}",
            "check": check,
            "severity": severity,
            "summary": summary,
            "recommendation": recommendation,
            "source": source,
        }
    )


def browser_check(status: str, summary: str, evidence: list[str] | None = None) -> dict[str, Any]:
    return {"status": status, "summary": summary, "evidence": evidence or []}


def parse_html_page(html_text: str) -> dict[str, Any]:
    parser = BrowserEvidenceHTMLParser()
    parser.feed(html_text)
    parser.close()
    return parser.page()


def count_snapshot_value(value: Any) -> int:
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, list):
        return len(value)
    return 0


def rendered_snapshot_console_errors(snapshot: dict[str, Any]) -> list[str]:
    raw_errors = snapshot.get("console_errors")
    if raw_errors is None:
        raw_errors = snapshot.get("errors")
    if raw_errors is None and isinstance(snapshot.get("console"), dict):
        raw_errors = snapshot["console"].get("errors")
    if isinstance(raw_errors, list):
        return [str(item) for item in raw_errors if str(item).strip()]
    if isinstance(raw_errors, str) and raw_errors.strip():
        return [raw_errors.strip()]
    return []


def rendered_snapshot_screenshot(snapshot: dict[str, Any]) -> str:
    for key in ("screenshot", "screenshot_path"):
        if non_empty_string(snapshot.get(key)):
            return str(snapshot[key])
    artifacts = snapshot.get("artifacts")
    if isinstance(artifacts, dict) and non_empty_string(artifacts.get("screenshot")):
        return str(artifacts["screenshot"])
    return ""


def page_from_rendered_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    raw_page = snapshot.get("page") if isinstance(snapshot.get("page"), dict) else snapshot
    title = str(raw_page.get("title", ""))
    text = str(raw_page.get("text") or raw_page.get("body_text") or raw_page.get("bodyText") or raw_page.get("visible_text") or "")
    raw_headings = raw_page.get("headings")
    headings = [str(item) for item in raw_headings if str(item).strip()] if isinstance(raw_headings, list) else []
    html_lang_raw = raw_page.get("html_lang")
    lang_raw = raw_page.get("lang")
    return {
        "title": title,
        "text_sample": text[:500],
        "_text_search": text,
        "text_length": len(text),
        "headings": headings[:12],
        "links": count_snapshot_value(raw_page.get("links")),
        "buttons": count_snapshot_value(raw_page.get("buttons")),
        "buttons_without_name": count_snapshot_value(raw_page.get("buttons_without_name")),
        "inputs": count_snapshot_value(raw_page.get("inputs")),
        "inputs_without_label": count_snapshot_value(raw_page.get("inputs_without_label")),
        "images": count_snapshot_value(raw_page.get("images")),
        "images_without_alt": count_snapshot_value(raw_page.get("images_without_alt")),
        "aria_labels": count_snapshot_value(raw_page.get("aria_labels")),
        "html_lang": bool(html_lang_raw) or non_empty_string(lang_raw),
    }


def fetch_url_text(url: str, timeout_seconds: int) -> tuple[str, str]:
    request = Request(url, headers={"User-Agent": "DriftlockBrowserEvidence/0"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            content_type = response.headers.get("content-type", "")
            charset_match = re.search(r"charset=([^;]+)", content_type, re.IGNORECASE)
            charset = charset_match.group(1).strip() if charset_match else "utf-8"
            body = response.read().decode(charset, errors="replace")
            return body, f"HTTP {getattr(response, 'status', 200)} {content_type}".strip()
    except HTTPError as exc:
        raise DriftlockError(f"Browser target returned HTTP {exc.code}: {url}") from exc
    except URLError as exc:
        raise DriftlockError(f"Browser target could not be reached: {url}: {exc.reason}") from exc


def screenshot_artifact_status(path_text: str | None) -> tuple[str, list[str]]:
    if not path_text:
        return "not_applicable", []
    path = Path(path_text)
    if path.exists() and path.is_file() and path.stat().st_size > 0:
        return "pass", [str(path)]
    return "fail", [str(path)]


def console_errors_from_path(path_text: str | None) -> list[str]:
    if not path_text:
        return []
    path = Path(path_text)
    if not path.exists():
        raise DriftlockError(f"Console errors file not found: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return [line.strip() for line in text.splitlines() if line.strip()]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, dict):
        raw_errors = value.get("errors") or value.get("console_errors") or []
        if isinstance(raw_errors, list):
            return [str(item) for item in raw_errors if str(item).strip()]
    return [text]


def build_browser_evidence(
    run_id: str,
    mode: str,
    source: str,
    html_text: str,
    expected_text: list[str] | None = None,
    viewport_name: str = "desktop",
    screenshot_path: str | None = None,
    console_errors_path: str | None = None,
    console_errors: list[str] | None = None,
    snapshot_page: dict[str, Any] | None = None,
    load_summary: str | None = None,
) -> dict[str, Any]:
    expected_text = expected_text or []
    viewport = dict(BROWSER_VIEWPORTS.get(viewport_name, BROWSER_VIEWPORTS["desktop"]))
    viewport["name"] = viewport_name if viewport_name in BROWSER_VIEWPORTS else "desktop"
    page = snapshot_page if isinstance(snapshot_page, dict) else parse_html_page(html_text)
    page_search_text = str(page.pop("_text_search", page.get("text_sample", "")))
    findings: list[dict[str, Any]] = []
    checks: dict[str, dict[str, Any]] = {}

    load_status = "pass" if html_text.strip() or page_search_text.strip() or non_empty_string(page.get("title")) else "fail"
    if load_status == "fail":
        browser_finding(findings, "load", "critical", "Browser target produced no HTML.", "Start the app or provide a reachable page before QA.", source)
    checks["load"] = browser_check(load_status, load_summary or ("Loaded target HTML." if load_status == "pass" else "Target did not load."), [source])

    title_status = "pass" if non_empty_string(page.get("title")) else "warning"
    if title_status == "warning":
        browser_finding(findings, "title", "medium", "Page title is empty.", "Add a meaningful title for browser QA and user orientation.", "page.title")
    checks["title"] = browser_check(title_status, "Page title is present." if title_status == "pass" else "Page title is missing.", [str(page.get("title", ""))])

    page_text = " ".join([str(page.get("title", "")), page_search_text]).lower()
    missing_expected = [item for item in expected_text if item.lower() not in page_text]
    if not expected_text:
        expected_status = "not_applicable"
        expected_summary = "No expected text assertions were requested."
    elif missing_expected:
        expected_status = "fail"
        expected_summary = "Expected text was not found in the page."
        browser_finding(
            findings,
            "expected_text",
            "high",
            f"Expected text missing: {', '.join(missing_expected)}.",
            "Verify the app rendered the approved surface or update the expected text.",
            "expected-text",
        )
    else:
        expected_status = "pass"
        expected_summary = "Expected text assertions passed."
    checks["expected_text"] = browser_check(expected_status, expected_summary, expected_text)

    collected_console_errors = list(console_errors or [])
    collected_console_errors.extend(console_errors_from_path(console_errors_path))
    if collected_console_errors:
        console_status = "fail"
        browser_finding(
            findings,
            "console",
            "high",
            f"Browser console errors were recorded: {len(collected_console_errors)}.",
            "Fix console errors or document why they are benign before handoff.",
            console_errors_path or "console",
        )
    elif console_errors_path:
        console_status = "pass"
    else:
        console_status = "not_applicable"
    checks["console"] = browser_check(
        console_status,
        "No console errors were recorded." if console_status == "pass" else ("Console error evidence was not provided." if console_status == "not_applicable" else "Console errors were recorded."),
        collected_console_errors[:5],
    )

    accessibility_issues = []
    if not page.get("html_lang"):
        accessibility_issues.append("html lang missing")
    if page.get("images_without_alt", 0):
        accessibility_issues.append(f"images_without_alt={page.get('images_without_alt')}")
    if page.get("inputs_without_label", 0):
        accessibility_issues.append(f"inputs_without_label={page.get('inputs_without_label')}")
    if page.get("buttons_without_name", 0):
        accessibility_issues.append(f"buttons_without_name={page.get('buttons_without_name')}")
    if accessibility_issues:
        accessibility_status = "warning"
        browser_finding(
            findings,
            "accessibility_baseline",
            "medium",
            f"Accessibility baseline has warnings: {', '.join(accessibility_issues)}.",
            "Add labels, alt text, button names, or html lang before production handoff.",
            "browser-accessibility-baseline",
        )
    else:
        accessibility_status = "pass"
    checks["accessibility_baseline"] = browser_check(
        accessibility_status,
        "Accessibility baseline passed." if accessibility_status == "pass" else "Accessibility baseline has warnings.",
        accessibility_issues,
    )

    responsive_status = "pass" if viewport["width"] >= 320 and viewport["height"] >= 568 else "warning"
    if responsive_status == "warning":
        browser_finding(findings, "responsive_baseline", "medium", "Viewport is below the supported smoke baseline.", "Run browser QA on mobile or desktop baseline viewport.", "viewport")
    checks["responsive_baseline"] = browser_check(responsive_status, "Viewport baseline is usable." if responsive_status == "pass" else "Viewport baseline is too small.", [f"{viewport['name']}={viewport['width']}x{viewport['height']}"])

    screenshot_status, screenshot_evidence = screenshot_artifact_status(screenshot_path)
    if screenshot_status == "fail":
        browser_finding(findings, "screenshot", "high", "Screenshot artifact path was provided but does not exist.", "Capture or attach the screenshot artifact before handoff.", screenshot_path or "screenshot")
    checks["screenshot"] = browser_check(
        screenshot_status,
        "Screenshot artifact exists." if screenshot_status == "pass" else ("Screenshot evidence was not requested." if screenshot_status == "not_applicable" else "Screenshot artifact is missing."),
        screenshot_evidence,
    )

    critical_findings = sum(1 for item in findings if item["severity"] == "critical")
    high_findings = sum(1 for item in findings if item["severity"] == "high")
    medium_findings = sum(1 for item in findings if item["severity"] == "medium")
    low_findings = sum(1 for item in findings if item["severity"] == "low")
    status = "fail" if critical_findings or high_findings else "pass"

    return {
        "run_id": run_id,
        "status": status,
        "mode": mode,
        "target": {
            "type": mode if mode in {"url", "html", "snapshot", "manual"} else "html",
            "source": source,
        },
        "captured_at": utc_now(),
        "upstream_source": {
            "repo": "gstack",
            "adapter": "driftlock-browser-qa",
            "paths": [
                "third_party/upstream/gstack/qa",
                "third_party/upstream/gstack/qa-only",
                "third_party/upstream/gstack/design-review",
                "third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-test-browser",
            ],
        },
        "viewport": viewport,
        "page": page,
        "checks": checks,
        "findings": findings,
        "metrics": {
            "total_findings": len(findings),
            "critical_findings": critical_findings,
            "high_findings": high_findings,
            "medium_findings": medium_findings,
            "low_findings": low_findings,
            "check_pass_count": sum(1 for item in checks.values() if item["status"] == "pass"),
            "check_fail_count": sum(1 for item in checks.values() if item["status"] == "fail"),
            "check_warning_count": sum(1 for item in checks.values() if item["status"] == "warning"),
            "check_not_applicable_count": sum(1 for item in checks.values() if item["status"] == "not_applicable"),
        },
        "artifacts": {
            "screenshot": screenshot_path or "",
            "console_errors": console_errors_path or "",
        },
    }


def quality_finding(
    findings: list[dict[str, Any]],
    check: str,
    severity: str,
    summary: str,
    recommendation: str,
    source: str,
    owner: str = "fixer",
) -> None:
    findings.append(
        {
            "id": f"QA-{len(findings) + 1:03d}",
            "check": check,
            "severity": severity,
            "summary": summary,
            "recommendation": recommendation,
            "source": source,
            "owner": owner,
        }
    )


def quality_check(status: str, summary: str, evidence: list[str] | None = None) -> dict[str, Any]:
    return {"status": status, "summary": summary, "evidence": evidence or []}


def command_statuses_pass(commands: Any) -> bool:
    if not isinstance(commands, list) or not commands:
        return False
    for command in commands:
        if not isinstance(command, dict):
            return False
        if command.get("status") != "pass":
            return False
    return True


def command_names(commands: Any) -> list[str]:
    if not isinstance(commands, list):
        return []
    names = []
    for command in commands:
        if isinstance(command, dict) and non_empty_string(command.get("cmd")):
            names.append(str(command["cmd"]))
    return names


def task_cover_ids_from_execution_plan(execution_plan: dict[str, Any]) -> set[str]:
    covered: set[str] = set()
    tasks = execution_plan.get("tasks")
    if isinstance(tasks, list):
        for task in tasks:
            if isinstance(task, dict) and isinstance(task.get("covers"), list):
                covered.update(item for item in task["covers"] if isinstance(item, str))
    return covered


def integration_evidence_status(spec: dict[str, Any], proof_bundle: dict[str, Any] | None = None) -> str:
    if proof_bundle:
        gates = proof_bundle.get("gates")
        if isinstance(gates, dict) and gates.get("integration") == "pass":
            return "pass"
    return evidence_status(explicit_evidence(spec, "integrations"))


def build_quality_report(
    run_id: str,
    spec: dict[str, Any],
    execution_plan: dict[str, Any],
    build_evidence: dict[str, Any],
    review_report: dict[str, Any],
    ux_lock_text: str = "",
    proof_bundle: dict[str, Any] | None = None,
    browser_evidence: dict[str, Any] | None = None,
    artifacts: dict[str, str] | None = None,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    checks: dict[str, dict[str, Any]] = {}
    spec_id = spec.get("id") if non_empty_string(spec.get("id")) else execution_plan.get("spec_id", "unknown-spec")
    proof_bundle = proof_bundle or {}
    browser_evidence = browser_evidence or {}
    browser_passed = bool(browser_evidence) and browser_evidence.get("status") == "pass"
    browser_target = ""
    if isinstance(browser_evidence.get("target"), dict):
        browser_target = str(browser_evidence["target"].get("source", ""))

    execution_status = "pass"
    execution_evidence: list[str] = []
    metrics = execution_plan.get("metrics")
    tasks = execution_plan.get("tasks")
    if execution_plan.get("status") != "done":
        execution_status = "fail"
        quality_finding(
            findings,
            "execution_completion",
            "critical",
            "Execution plan is not complete.",
            "Finish all task execution loops before QA and handoff.",
            "execution-plan.status",
        )
    if isinstance(metrics, dict):
        execution_evidence.append(f"done={metrics.get('done')} total={metrics.get('total')} blocked={metrics.get('blocked')}")
        if metrics.get("total") != metrics.get("done"):
            execution_status = "fail"
            quality_finding(
                findings,
                "execution_completion",
                "critical",
                "Not all execution tasks are done.",
                "Return unfinished tasks through implementer, builder, reviewer, fixer, or compound as required.",
                "execution-plan.metrics",
            )
        if metrics.get("blocked", 0):
            execution_status = "fail"
            quality_finding(
                findings,
                "execution_completion",
                "high",
                "Execution plan still contains blocked tasks.",
                "Resolve blocked tasks or request an amendment before QA can pass.",
                "execution-plan.metrics.blocked",
            )
    else:
        execution_status = "fail"
        quality_finding(findings, "execution_completion", "critical", "Execution metrics are missing.", "Refresh execution-status before QA.", "execution-plan.metrics")
    if isinstance(tasks, list):
        not_done = [task.get("task_id", "unknown") for task in tasks if isinstance(task, dict) and task.get("state") != "TASK_DONE"]
        if not_done:
            execution_status = "fail"
            quality_finding(
                findings,
                "execution_completion",
                "critical",
                f"Tasks are not done: {', '.join(str(item) for item in not_done)}.",
                "Complete every task state before QA.",
                "execution-plan.tasks",
            )
    checks["execution_completion"] = quality_check(execution_status, "All task states are complete." if execution_status == "pass" else "Execution loop is incomplete.", execution_evidence)

    build_status = "pass" if build_evidence.get("status") == "pass" and command_statuses_pass(build_evidence.get("commands")) else "fail"
    if build_status == "fail":
        quality_finding(
            findings,
            "build_verification",
            "critical",
            "Build evidence did not pass.",
            "Route to fixer and rerun builder verification.",
            "build-evidence",
        )
    checks["build_verification"] = quality_check(
        build_status,
        "Build and command evidence passed." if build_status == "pass" else "Build evidence is failing or incomplete.",
        command_names(build_evidence.get("commands")),
    )

    review_status = "pass"
    if review_report.get("status") != "approved":
        review_status = "fail"
        quality_finding(findings, "review_integrity", "critical", "Review report is not approved.", "Route rejected findings to fixer or compound.", "review-report.status")
    if review_report.get("reviewer_read_only") is not True or review_report.get("code_edits_made") is not False:
        review_status = "fail"
        quality_finding(
            findings,
            "review_integrity",
            "critical",
            "Reviewer integrity contract was violated.",
            "Discard reviewer code edits and rerun review as read-only.",
            "review-report.reviewer_read_only",
            "compound",
        )
    critical_review_findings = []
    for item in review_report.get("findings", []):
        if isinstance(item, dict) and item.get("severity") in {"P0", "P1"} and item.get("requires_verification") is True:
            critical_review_findings.append(item.get("summary", "unresolved finding"))
    if critical_review_findings:
        review_status = "fail"
        quality_finding(
            findings,
            "review_integrity",
            "high",
            f"Review has unresolved high-priority findings: {len(critical_review_findings)}.",
            "Resolve high-priority review findings before QA passes.",
            "review-report.findings",
        )
    checks["review_integrity"] = quality_check(review_status, "Review integrity passed." if review_status == "pass" else "Review integrity failed.", critical_review_findings)

    product_shape = spec.get("product_shape")
    ux_status = "pass"
    ux_evidence = []
    if isinstance(product_shape, dict):
        ux_evidence.append(f"approved_preview={product_shape.get('approved_preview')}")
    if browser_evidence:
        page = browser_evidence.get("page")
        if isinstance(page, dict):
            ux_evidence.append(f"browser_title={page.get('title', '')}")
        if browser_target:
            ux_evidence.append(f"browser_target={browser_target}")
        if browser_evidence.get("status") == "fail":
            ux_status = "fail"
            quality_finding(
                findings,
                "ux_alignment",
                "high",
                "Browser QA evidence failed for the delivered surface.",
                "Return to fixer or UX guard and refresh browser-evidence.json.",
                "browser-evidence.status",
            )
    if not isinstance(product_shape, dict) or product_shape.get("approved_preview") is not True:
        ux_status = "fail"
        quality_finding(
            findings,
            "ux_alignment",
            "critical",
            "Approved UX preview evidence is missing.",
            "Return to UX approval or request an amendment before QA passes.",
            "locked-spec.product_shape.approved_preview",
            "amend-advisor",
        )
    if ux_lock_text.strip():
        ux_evidence.append("ux-lock.md present")
        if "Approved" not in ux_lock_text and "approved" not in ux_lock_text:
            ux_status = "fail"
            quality_finding(
                findings,
                "ux_alignment",
                "high",
                "UX lock does not contain approval evidence.",
                "Regenerate ux-lock.md from the approved UX preview.",
                "ux-lock.md",
                "amend-advisor",
            )
    else:
        ux_status = "fail"
        quality_finding(
            findings,
            "ux_alignment",
            "high",
            "UX lock artifact is missing.",
            "Run UX guard with the approved UX lock before QA.",
            "ux-lock.md",
            "amend-advisor",
        )
    checks["ux_alignment"] = quality_check(ux_status, "UX approval and lock evidence are present." if ux_status == "pass" else "UX alignment evidence is incomplete.", ux_evidence)

    required_covers = spec_cover_ids(spec)
    actual_covers = task_cover_ids_from_execution_plan(execution_plan)
    missing_covers = sorted(required_covers - actual_covers)
    coverage_status = "pass" if required_covers and not missing_covers else "fail"
    if not required_covers:
        quality_finding(
            findings,
            "acceptance_coverage",
            "high",
            "Spec has no acceptance coverage IDs.",
            "Return to spec gate and add testable success criteria or scenarios.",
            "locked-spec.success_criteria",
            "amend-advisor",
        )
    if missing_covers:
        quality_finding(
            findings,
            "acceptance_coverage",
            "high",
            f"Execution plan does not cover: {', '.join(missing_covers)}.",
            "Split or add tasks until every success criterion and acceptance scenario is covered.",
            "execution-plan.tasks.covers",
        )
    checks["acceptance_coverage"] = quality_check(
        coverage_status,
        "Execution tasks cover all success criteria and scenarios." if coverage_status == "pass" else "Acceptance coverage is incomplete.",
        sorted(actual_covers),
    )

    commands = command_names(build_evidence.get("commands"))
    smoke_terms = ("test", "lint", "build", "typecheck", "e2e", "playwright", "vitest", "pytest")
    command_smoke = any(any(term in command.lower() for term in smoke_terms) for command in commands)
    has_smoke = command_smoke or browser_passed
    regression_status = "pass" if build_status == "pass" and has_smoke and browser_passed else "fail"
    if not has_smoke:
        quality_finding(
            findings,
            "regression_smoke",
            "high",
            "No recognizable regression smoke command was recorded.",
            "Run at least one test, lint, build, typecheck, or browser smoke command before QA passes.",
            "build-evidence.commands",
        )
    if not browser_evidence:
        quality_finding(
            findings,
            "regression_smoke",
            "high",
            "Browser QA evidence is missing.",
            "Run browser-collect against the delivered surface before final QA.",
            "browser-evidence.json",
        )
    elif browser_evidence.get("status") == "fail":
        quality_finding(
            findings,
            "regression_smoke",
            "high",
            "Browser QA evidence failed.",
            "Fix the delivered surface and refresh browser-evidence.json.",
            "browser-evidence.status",
        )
    checks["regression_smoke"] = quality_check(
        regression_status,
        "Regression smoke command evidence is present." if regression_status == "pass" else "Regression smoke evidence is missing.",
        commands + ([f"browser-evidence={browser_target or 'present'}"] if browser_passed else []),
    )

    integration_status = integration_evidence_status(spec, proof_bundle)
    if integration_status == "fail":
        quality_finding(
            findings,
            "integration_readiness",
            "high",
            "Integration evidence is missing.",
            "Add integration checks or explicitly mark integrations not applicable with a reason.",
            "locked-spec.spec_evidence.integrations",
            "amend-advisor",
        )
    checks["integration_readiness"] = quality_check(
        integration_status,
        "Integration evidence is present." if integration_status == "pass" else ("Integrations are explicitly not applicable." if integration_status == "not_applicable" else "Integration evidence is missing."),
        [str(explicit_evidence(spec, "integrations"))],
    )

    accessibility_evidence = explicit_evidence(spec, "accessibility")
    browser_accessibility = None
    if isinstance(browser_evidence.get("checks"), dict):
        browser_accessibility = browser_evidence["checks"].get("accessibility_baseline")
    if isinstance(browser_accessibility, dict) and browser_accessibility.get("status") in {"pass", "warning", "fail"}:
        accessibility_status = str(browser_accessibility["status"])
        accessibility_sources = [f"browser-evidence={browser_accessibility.get('summary')}"]
        if accessibility_status == "fail":
            quality_finding(
                findings,
                "accessibility_baseline",
                "high",
                "Browser accessibility baseline failed.",
                "Resolve accessibility failures from browser-evidence.json before handoff.",
                "browser-evidence.checks.accessibility_baseline",
                "fixer",
            )
        elif accessibility_status == "warning":
            for item in browser_evidence.get("findings", []):
                if isinstance(item, dict) and item.get("check") == "accessibility_baseline":
                    quality_finding(
                        findings,
                        "accessibility_baseline",
                        item.get("severity", "medium"),
                        item.get("summary", "Browser accessibility baseline has warnings."),
                        item.get("recommendation", "Resolve browser accessibility warnings before production handoff."),
                        item.get("source", "browser-evidence"),
                        "handoff",
                    )
    else:
        accessibility_status = evidence_status(accessibility_evidence)
        accessibility_sources = [str(accessibility_evidence)] if accessibility_evidence is not None else []
    if accessibility_status == "fail":
        accessibility_status = "warning"
        quality_finding(
            findings,
            "accessibility_baseline",
            "medium",
            "Accessibility baseline evidence is missing.",
            "Add keyboard, contrast, label, or screen-reader smoke evidence before production handoff.",
            "locked-spec.spec_evidence.accessibility",
            "handoff",
        )
    checks["accessibility_baseline"] = quality_check(
        accessibility_status,
        "Accessibility baseline evidence is present." if accessibility_status == "pass" else "Accessibility baseline is missing but not release-blocking in v0.",
        accessibility_sources,
    )

    proof_status = "pass"
    proof_gates = proof_bundle.get("gates")
    if isinstance(proof_gates, dict):
        for gate in ("ux_guard", "build", "review", "amendment", "integration"):
            if proof_gates.get(gate) != "pass":
                proof_status = "fail"
                quality_finding(
                    findings,
                    "proof_readiness",
                    "high",
                    f"Proof bundle gate `{gate}` is not pass.",
                    "Complete all upstream gates before final QA.",
                    f"proof-bundle.gates.{gate}",
                )
    else:
        proof_status = "fail"
        quality_finding(
            findings,
            "proof_readiness",
            "high",
            "Proof bundle gates are missing.",
            "Initialize or refresh proof-bundle.json before final handoff.",
            "proof-bundle.gates",
        )
    checks["proof_readiness"] = quality_check(
        proof_status,
        "Proof bundle prerequisite gates are ready." if proof_status == "pass" else "Proof bundle is not ready.",
        [f"{key}={value}" for key, value in proof_gates.items()] if isinstance(proof_gates, dict) else [],
    )

    critical_findings = sum(1 for item in findings if item["severity"] == "critical")
    high_findings = sum(1 for item in findings if item["severity"] == "high")
    medium_findings = sum(1 for item in findings if item["severity"] == "medium")
    low_findings = sum(1 for item in findings if item["severity"] == "low")
    report_status = "fail" if critical_findings or high_findings else "pass"
    if report_status == "pass":
        next_route = "driftlock-handoff"
    elif any(item["owner"] == "amend-advisor" for item in findings if item["severity"] in QUALITY_FAIL_SEVERITIES):
        next_route = "driftlock-amend-advisor"
    elif sum(1 for item in findings if item["severity"] in QUALITY_FAIL_SEVERITIES) >= 3:
        next_route = "driftlock-compound"
    else:
        next_route = "driftlock-fixer"

    return {
        "run_id": run_id,
        "spec_id": spec_id,
        "status": report_status,
        "upstream_source": {
            "repo": "gstack",
            "adapter": "driftlock-quality-gate",
            "paths": [
                "third_party/upstream/gstack/qa",
                "third_party/upstream/gstack/qa-only",
                "third_party/upstream/gstack/ship",
                "third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-proof",
                "third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-browser-test",
            ],
        },
        "checks": checks,
        "findings": findings,
        "metrics": {
            "total_findings": len(findings),
            "critical_findings": critical_findings,
            "high_findings": high_findings,
            "medium_findings": medium_findings,
            "low_findings": low_findings,
            "check_pass_count": sum(1 for item in checks.values() if item["status"] == "pass"),
            "check_fail_count": sum(1 for item in checks.values() if item["status"] == "fail"),
            "check_warning_count": sum(1 for item in checks.values() if item["status"] == "warning"),
            "check_not_applicable_count": sum(1 for item in checks.values() if item["status"] == "not_applicable"),
        },
        "next_route": next_route,
        "artifacts": artifacts
        or {
            "locked_spec": "locked-spec.json",
            "execution_plan": "execution-plan.json",
            "build_evidence": "build-evidence.json",
            "review_report": "review-report.json",
            "ux_lock": "ux-lock.md",
            "browser_evidence": "browser-evidence.json",
            "proof_bundle": "proof-bundle.json",
        },
    }


def severity_rank(severity: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(severity, 0)


def highest_severity(severities: list[str]) -> str:
    valid = [severity for severity in severities if severity in QUALITY_SEVERITIES]
    if not valid:
        return "medium"
    return sorted(valid, key=severity_rank, reverse=True)[0]


def ce_owner_from_route(route_owner: str | None) -> str:
    if route_owner == "amend-advisor":
        return "amend-advisor"
    if route_owner == "human":
        return "fixer"
    if route_owner in {"fixer", "compound"}:
        return route_owner
    return "fixer"


def collect_task_attempt_evidence(execution_plan: dict[str, Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    tasks = execution_plan.get("tasks")
    if not isinstance(tasks, list):
        return evidence
    for task in tasks:
        if not isinstance(task, dict):
            continue
        attempts = task.get("attempts")
        if not isinstance(attempts, dict):
            continue
        repeated_fields = [
            ("build_attempts", "build attempts"),
            ("review_attempts", "review attempts"),
            ("fix_attempts", "fix attempts"),
            ("ce_cycles", "CE cycles"),
        ]
        repeated = [f"{label}={attempts.get(field)}" for field, label in repeated_fields if isinstance(attempts.get(field), int) and attempts.get(field) >= 2]
        if isinstance(attempts.get("ce_cycles"), int) and attempts.get("ce_cycles") >= 1 and not repeated:
            repeated.append(f"CE cycles={attempts.get('ce_cycles')}")
        if repeated:
            evidence.append(
                {
                    "task_id": task.get("task_id", "unknown-task"),
                    "summary": f"Task {task.get('task_id', 'unknown-task')} shows repeated or escalated failure: {', '.join(repeated)}.",
                    "source": f"execution-plan.tasks.{task.get('task_id', 'unknown-task')}.attempts",
                }
            )
    return evidence


def add_ce_cluster(
    clusters: dict[str, dict[str, Any]],
    kind: str,
    severity: str,
    summary: str,
    evidence: str,
    owner: str,
) -> None:
    key = kind
    cluster = clusters.setdefault(
        key,
        {
            "id": f"CE-{len(clusters) + 1:03d}",
            "kind": kind,
            "severity": severity,
            "summary": summary,
            "evidence": [],
            "owners": [],
        },
    )
    cluster["severity"] = highest_severity([cluster["severity"], severity])
    if summary not in cluster["summary"]:
        cluster["summary"] = summary if len(summary) > len(cluster["summary"]) else cluster["summary"]
    if evidence not in cluster["evidence"]:
        cluster["evidence"].append(evidence)
    if owner not in cluster["owners"]:
        cluster["owners"].append(owner)


def build_ce_synthesis(
    run_id: str,
    spec: dict[str, Any],
    execution_plan: dict[str, Any],
    review_report: dict[str, Any],
    quality_report: dict[str, Any] | None = None,
    build_evidence: dict[str, Any] | None = None,
    artifacts: dict[str, str] | None = None,
) -> dict[str, Any]:
    clusters: dict[str, dict[str, Any]] = {}
    spec_id = spec.get("id") if non_empty_string(spec.get("id")) else execution_plan.get("spec_id", "unknown-spec")
    build_evidence = build_evidence or {}
    quality_report = quality_report or {}

    if build_evidence.get("status") == "fail":
        add_ce_cluster(
            clusters,
            "build_failure",
            "high",
            "Build evidence failed before review could safely pass.",
            "build-evidence.status=fail",
            "fixer",
        )

    if review_report.get("status") == "rejected":
        add_ce_cluster(
            clusters,
            "review_reject",
            "high",
            "Reviewer rejected the implementation and the failure needs synthesis before another retry.",
            "review-report.status=rejected",
            "fixer",
        )
    if review_report.get("reviewer_read_only") is not True or review_report.get("code_edits_made") is not False:
        add_ce_cluster(
            clusters,
            "review_integrity",
            "critical",
            "Reviewer integrity contract was violated.",
            "review-report reviewer_read_only/code_edits_made",
            "compound",
        )
    review_findings = review_report.get("findings")
    if isinstance(review_findings, list):
        for index, item in enumerate(review_findings):
            if not isinstance(item, dict):
                continue
            if item.get("owner") == "amend-advisor":
                add_ce_cluster(
                    clusters,
                    "product_intent_conflict",
                    "high",
                    item.get("summary", "Review finding may change product intent."),
                    f"review-report.findings[{index}]",
                    "amend-advisor",
                )
            elif item.get("severity") in {"P0", "P1"} or item.get("requires_verification") is True:
                add_ce_cluster(
                    clusters,
                    "review_reject",
                    "high" if item.get("severity") in {"P0", "P1"} else "medium",
                    item.get("summary", "Review finding requires another verified fix loop."),
                    f"review-report.findings[{index}]",
                    ce_owner_from_route(item.get("owner")),
                )

    if quality_report.get("status") == "fail":
        add_ce_cluster(
            clusters,
            "quality_failure",
            "high",
            "Quality gate failed and must be translated into a fix strategy before retrying.",
            "quality-report.status=fail",
            "fixer",
        )
    quality_findings = quality_report.get("findings")
    if isinstance(quality_findings, list):
        for index, item in enumerate(quality_findings):
            if not isinstance(item, dict):
                continue
            if item.get("severity") not in QUALITY_FAIL_SEVERITIES:
                continue
            kind = "product_intent_conflict" if item.get("owner") == "amend-advisor" else "quality_failure"
            add_ce_cluster(
                clusters,
                kind,
                item.get("severity", "high"),
                item.get("summary", "Quality finding requires synthesis."),
                f"quality-report.findings[{index}]",
                ce_owner_from_route(item.get("owner")),
            )

    for item in collect_task_attempt_evidence(execution_plan):
        add_ce_cluster(
            clusters,
            "repeated_failure",
            "high",
            item["summary"],
            item["source"],
            "compound",
        )

    if not clusters:
        add_ce_cluster(
            clusters,
            "repeated_failure",
            "medium",
            "CE was invoked without concrete repeated-failure evidence.",
            "missing CE trigger evidence",
            "fixer",
        )
        status = "blocked"
    else:
        status = "ready"

    cluster_list = list(clusters.values())
    trigger_cluster = sorted(cluster_list, key=lambda item: severity_rank(item["severity"]), reverse=True)[0]
    may_change_product_intent = any(cluster["kind"] == "product_intent_conflict" or "amend-advisor" in cluster["owners"] for cluster in cluster_list)
    if may_change_product_intent:
        return_route = "driftlock-amend-advisor"
        strategy_owner = "amend-advisor"
    else:
        return_route = "driftlock-fixer"
        strategy_owner = "fixer"

    evidence_lines = [evidence for cluster in cluster_list for evidence in cluster["evidence"]]
    what_did_not_work = []
    if review_report.get("status") == "rejected":
        what_did_not_work.append("Prior implementation reached reviewer but did not satisfy review criteria.")
    if build_evidence.get("status") == "fail":
        what_did_not_work.append("Prior implementation did not produce passing build evidence.")
    if quality_report.get("status") == "fail":
        what_did_not_work.append("Prior implementation did not satisfy final Quality/QA gate.")
    if any(cluster["kind"] == "repeated_failure" for cluster in cluster_list):
        what_did_not_work.append("Retrying without changing the fix hypothesis has already escalated into CE.")

    learning_status = "required" if any(cluster["kind"] == "repeated_failure" for cluster in cluster_list) else "not-needed"
    learning_key = "-".join(sorted({cluster["kind"] for cluster in cluster_list}))[:80]
    if not learning_key:
        learning_key = "ce-no-trigger"
    prevention_rule = "Before retrying, state the root-cause hypothesis, the evidence that supports it, and the verification command that will disprove it."

    return {
        "run_id": run_id,
        "spec_id": str(spec_id),
        "status": status,
        "upstream_source": {
            "repo": "compound-engineering-plugin",
            "adapter": "driftlock-ce-synthesis",
            "paths": [
                "third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-compound",
                "third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-debug",
                "third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-compound/references/schema.yaml",
                "third_party/upstream/gstack/learn",
                "third_party/upstream/gstack/context-save",
            ],
        },
        "trigger": {
            "kind": trigger_cluster["kind"],
            "severity": trigger_cluster["severity"],
            "summary": trigger_cluster["summary"],
            "source": trigger_cluster["evidence"][0],
        },
        "failure_clusters": cluster_list,
        "root_cause_hypothesis": {
            "summary": "The current failure loop is likely caused by an untested assumption in the previous fix strategy, not by a lack of another retry.",
            "confidence": "medium" if status == "ready" else "low",
            "supporting_evidence": evidence_lines or ["CE invoked without sufficient evidence."],
        },
        "what_did_not_work": what_did_not_work,
        "next_fix_strategy": {
            "owner": strategy_owner,
            "steps": [
                "Pick one failure cluster and write the smallest falsifiable fix hypothesis.",
                "Change only the code or spec surface needed for that hypothesis.",
                "Run the build, regression smoke, and review evidence that previously failed.",
                "Return through implementer/fixer, then builder, then reviewer before QA or handoff.",
            ],
        },
        "verification_plan": [
            "Rerun the failed build or smoke command.",
            "Refresh review-report.json with reviewer_read_only=true and code_edits_made=false.",
            "Refresh quality-report.json before handoff.",
        ],
        "learning_note": {
            "status": learning_status,
            "key": learning_key,
            "summary": "Capture this repeated failure pattern if the next fix succeeds.",
            "prevention_rule": prevention_rule,
        },
        "intent_impact": {
            "may_change_product_intent": may_change_product_intent,
            "amendment_required": may_change_product_intent,
            "reason": "Failure evidence is owned by amend advisor." if may_change_product_intent else "Failure can be handled inside the locked implementation intent.",
        },
        "return_route": return_route,
        "forbidden_routes": sorted(CE_FORBIDDEN_ROUTES),
        "artifacts": artifacts
        or {
            "review_report": "review-report.json",
            "quality_report": "quality-report.json",
            "execution_plan": "execution-plan.json",
            "build_evidence": "build-evidence.json",
        },
    }


def render_ce_brief(synthesis: dict[str, Any]) -> str:
    clusters = synthesis.get("failure_clusters", [])
    cluster_lines = []
    if isinstance(clusters, list):
        for cluster in clusters:
            if isinstance(cluster, dict):
                cluster_lines.append(f"- {cluster.get('kind')}: {cluster.get('summary')} ({cluster.get('severity')})")
    what_did_not_work = synthesis.get("what_did_not_work", [])
    failed_lines = [f"- {item}" for item in what_did_not_work] if isinstance(what_did_not_work, list) else []
    strategy = synthesis.get("next_fix_strategy", {})
    steps = strategy.get("steps", []) if isinstance(strategy, dict) else []
    step_lines = [f"- {step}" for step in steps] if isinstance(steps, list) else []
    verification = synthesis.get("verification_plan", [])
    verification_lines = [f"- {item}" for item in verification] if isinstance(verification, list) else []
    intent = synthesis.get("intent_impact", {})
    learning = synthesis.get("learning_note", {})
    hypothesis = synthesis.get("root_cause_hypothesis", {})

    return "\n".join(
        [
            "# CE Brief",
            "",
            f"Run: {synthesis.get('run_id')}",
            f"Spec: {synthesis.get('spec_id')}",
            f"Status: {synthesis.get('status')}",
            f"Return route: {synthesis.get('return_route')}",
            "",
            "## Trigger",
            "",
            f"{synthesis.get('trigger', {}).get('summary', 'No trigger summary.')}",
            "",
            "## Failure Clusters",
            "",
            *(cluster_lines or ["- No concrete failure cluster was found."]),
            "",
            "## Root-Cause Hypothesis",
            "",
            f"{hypothesis.get('summary', 'No hypothesis recorded.')}",
            "",
            "## What Did Not Work",
            "",
            *(failed_lines or ["- No prior failed attempt was recorded."]),
            "",
            "## Next Fix Strategy",
            "",
            *(step_lines or ["- Return to fixer with a falsifiable hypothesis."]),
            "",
            "## Verification Plan",
            "",
            *(verification_lines or ["- Refresh build, review, and quality evidence."]),
            "",
            "## Intent Impact",
            "",
            f"Amendment required: {intent.get('amendment_required')}",
            f"Reason: {intent.get('reason')}",
            "",
            "## Learning Note",
            "",
            f"Status: {learning.get('status')}",
            f"Key: {learning.get('key')}",
            f"Prevention: {learning.get('prevention_rule')}",
            "",
        ]
    )


def build_spec_gate_report(
    spec: dict[str, Any],
    ux_lock_text: str = "",
    decision_log: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    categories: dict[str, dict[str, str]] = {}

    spec_id = spec.get("id") if non_empty_string(spec.get("id")) else "unknown-spec"

    goals_ok = non_empty_string_list(spec.get("goals"))
    non_goals_ok = non_empty_string_list(spec.get("non_goals"))
    functional_status = "pass" if goals_ok and non_goals_ok else "fail"
    if not goals_ok:
        finding(findings, "functional_scope", "high", "Locked Spec goals are missing or empty.", "Add concrete v1 goals before task split.", "locked-spec.goals")
    if not non_goals_ok:
        finding(findings, "functional_scope", "medium", "Locked Spec non-goals are missing or empty.", "Add explicit non-goals to prevent scope drift.", "locked-spec.non_goals")
    categories["functional_scope"] = {
        "status": functional_status,
        "summary": category_summary(functional_status, "Goals and non-goals are explicit.", "Functional scope is underspecified."),
    }

    data_status = evidence_status(explicit_evidence(spec, "data_model"))
    if data_status == "fail":
        finding(findings, "data_model", "medium", "No explicit data model evidence was provided.", "Add data model notes or mark data model as not_applicable with a reason.", "locked-spec.spec_evidence.data_model")
    categories["data_model"] = {
        "status": data_status,
        "summary": category_summary(data_status, "Data model evidence is present.", "Data model evidence is missing.", "Data model is explicitly not applicable."),
    }

    product_shape = spec.get("product_shape")
    ux_status = "pass"
    if not isinstance(product_shape, dict):
        ux_status = "fail"
        finding(findings, "ux_flow", "critical", "Product shape object is missing.", "Return to UX preview and product lock before spec gate.", "locked-spec.product_shape")
    else:
        if product_shape.get("approved_preview") is not True:
            ux_status = "fail"
            finding(findings, "ux_flow", "critical", "Approved UX preview is missing.", "Get explicit UX preview approval before locking the spec.", "locked-spec.product_shape.approved_preview")
        for field in ("primary_user", "first_screen", "core_flow", "approval_source"):
            if not non_empty_string(product_shape.get(field)):
                ux_status = "fail"
                finding(findings, "ux_flow", "high", f"Product shape field `{field}` is missing.", f"Fill product_shape.{field} before task split.", f"locked-spec.product_shape.{field}")
        if not non_empty_string_list(product_shape.get("ux_principles")):
            ux_status = "fail"
            finding(findings, "ux_flow", "high", "UX principles are missing.", "Add UX principles that implementation must preserve.", "locked-spec.product_shape.ux_principles")
    if ux_lock_text.strip() and "Approved" not in ux_lock_text:
        ux_status = "fail"
        finding(findings, "ux_flow", "high", "UX lock exists but does not contain approval evidence.", "Record approved preview evidence in ux-lock.md.", "ux-lock")
    if decision_log is not None and len(decision_log) > 0 and accepted_decision_count(decision_log) == 0:
        ux_status = "fail"
        finding(findings, "ux_flow", "high", "Decision log has no accepted decisions.", "Record the accepted UX/product decisions before task split.", "decision-log")
    categories["ux_flow"] = {
        "status": ux_status,
        "summary": category_summary(ux_status, "Approved product shape and UX evidence are present.", "UX/product-shape evidence is incomplete."),
    }

    nfr_status = evidence_status(explicit_evidence(spec, "non_functional_quality"))
    if nfr_status == "fail":
        finding(findings, "non_functional_quality", "medium", "No explicit non-functional quality evidence was provided.", "Add measurable quality constraints or mark not_applicable with a reason.", "locked-spec.spec_evidence.non_functional_quality")
    categories["non_functional_quality"] = {
        "status": nfr_status,
        "summary": category_summary(nfr_status, "Non-functional quality evidence is present.", "Non-functional quality is underspecified.", "Non-functional quality is explicitly not applicable."),
    }

    integration_status = evidence_status(explicit_evidence(spec, "integrations"))
    if integration_status == "fail":
        finding(findings, "integrations", "medium", "No explicit integration evidence was provided.", "Add integration/dependency notes or mark not_applicable with a reason.", "locked-spec.spec_evidence.integrations")
    categories["integrations"] = {
        "status": integration_status,
        "summary": category_summary(integration_status, "Integration evidence is present.", "Integration evidence is missing.", "Integrations are explicitly not applicable."),
    }

    edge_status = evidence_status(explicit_evidence(spec, "edge_failure"))
    if edge_status == "fail":
        finding(findings, "edge_failure", "medium", "No explicit edge/failure handling evidence was provided.", "Add edge cases and expected failure behavior before implementation.", "locked-spec.spec_evidence.edge_failure")
    categories["edge_failure"] = {
        "status": edge_status,
        "summary": category_summary(edge_status, "Edge/failure handling evidence is present.", "Edge/failure handling is underspecified.", "Edge/failure handling is explicitly not applicable."),
    }

    constraints_status = evidence_status(explicit_evidence(spec, "constraints_tradeoffs"))
    if constraints_status == "fail":
        finding(findings, "constraints_tradeoffs", "medium", "No explicit constraints/tradeoffs evidence was provided.", "Document constraints, tradeoffs, or rejected alternatives.", "locked-spec.spec_evidence.constraints_tradeoffs")
    categories["constraints_tradeoffs"] = {
        "status": constraints_status,
        "summary": category_summary(constraints_status, "Constraints/tradeoffs evidence is present.", "Constraints/tradeoffs are underspecified.", "Constraints/tradeoffs are explicitly not applicable."),
    }

    terminology_status = evidence_status(explicit_evidence(spec, "terminology"))
    if terminology_status == "fail":
        finding(findings, "terminology", "medium", "No explicit terminology evidence was provided.", "Add canonical terms or glossary notes to prevent agent drift.", "locked-spec.spec_evidence.terminology")
    categories["terminology"] = {
        "status": terminology_status,
        "summary": category_summary(terminology_status, "Terminology evidence is present.", "Terminology is underspecified.", "Terminology is explicitly not applicable."),
    }

    completion_status = "pass"
    success_criteria = spec.get("success_criteria")
    scenarios = spec.get("acceptance_scenarios")
    if not isinstance(success_criteria, list) or not success_criteria:
        completion_status = "fail"
        finding(findings, "completion_signals", "critical", "Success criteria are missing.", "Add testable success criteria before task split.", "locked-spec.success_criteria")
    elif any(not isinstance(item, dict) or item.get("testable") is not True for item in success_criteria):
        completion_status = "fail"
        finding(findings, "completion_signals", "high", "One or more success criteria are not testable.", "Make every success criterion explicitly testable.", "locked-spec.success_criteria")
    if not isinstance(scenarios, list) or not scenarios:
        completion_status = "fail"
        finding(findings, "completion_signals", "critical", "Acceptance scenarios are missing.", "Add Given/When/Then acceptance scenarios.", "locked-spec.acceptance_scenarios")
    else:
        for index, scenario in enumerate(scenarios):
            if not isinstance(scenario, dict) or any(not non_empty_string(scenario.get(field)) for field in ("given", "when", "then")):
                completion_status = "fail"
                finding(findings, "completion_signals", "high", f"Acceptance scenario {index + 1} is incomplete.", "Fill given/when/then for every acceptance scenario.", f"locked-spec.acceptance_scenarios[{index}]")
    decision_policy = spec.get("decision_policy")
    if not isinstance(decision_policy, list):
        completion_status = "fail"
        finding(findings, "completion_signals", "high", "Decision policy is missing.", "Add all Driftlock decision policy classes.", "locked-spec.decision_policy")
    else:
        classes = {item.get("class") for item in decision_policy if isinstance(item, dict)}
        missing_classes = sorted(DECISION_CLASSES - classes)
        if missing_classes:
            completion_status = "fail"
            finding(findings, "completion_signals", "high", f"Decision policy is missing classes: {', '.join(missing_classes)}.", "Add complete decision policy coverage.", "locked-spec.decision_policy")
    categories["completion_signals"] = {
        "status": completion_status,
        "summary": category_summary(completion_status, "Success criteria, acceptance scenarios, and decision policy are testable.", "Completion signals are incomplete."),
    }

    placeholder_status = "pass"
    spec_text = json.dumps(spec, ensure_ascii=False, sort_keys=True)
    found_placeholders = [marker for marker in SPEC_GATE_PLACEHOLDERS if marker in spec_text]
    if found_placeholders:
        placeholder_status = "fail"
        finding(
            findings,
            "placeholders",
            "high",
            f"Locked Spec contains unresolved placeholder markers: {', '.join(found_placeholders)}.",
            "Resolve placeholders before product lock or route back to clarification.",
            "locked-spec",
        )
    categories["placeholders"] = {
        "status": placeholder_status,
        "summary": category_summary(placeholder_status, "No unresolved placeholder markers were found.", "Unresolved placeholders remain in the Locked Spec."),
    }

    critical_findings = sum(1 for item in findings if item["severity"] == "critical")
    high_findings = sum(1 for item in findings if item["severity"] == "high")
    medium_findings = sum(1 for item in findings if item["severity"] == "medium")
    low_findings = sum(1 for item in findings if item["severity"] == "low")
    report_status = "fail" if critical_findings or high_findings else "pass"
    product_intent_categories = {"functional_scope", "ux_flow", "completion_signals", "placeholders"}
    intent_affecting_failure = any(
        item["severity"] in {"critical", "high"} and item["category"] in product_intent_categories for item in findings
    )
    next_route = "driftlock-task-split" if report_status == "pass" else ("driftlock-amend-advisor" if intent_affecting_failure else "driftlock-product-lock")

    return {
        "spec_id": spec_id,
        "status": report_status,
        "upstream_source": {
            "repo": "spec-kit",
            "adapter": "driftlock-spec-gate",
            "paths": [
                "third_party/upstream/spec-kit/templates/commands/clarify.md",
                "third_party/upstream/spec-kit/templates/commands/analyze.md",
                "third_party/upstream/spec-kit/templates/commands/specify.md",
                "third_party/upstream/spec-kit/templates/checklist-template.md",
            ],
        },
        "categories": categories,
        "findings": findings,
        "metrics": {
            "total_findings": len(findings),
            "critical_findings": critical_findings,
            "high_findings": high_findings,
            "medium_findings": medium_findings,
            "low_findings": low_findings,
            "category_pass_count": sum(1 for item in categories.values() if item["status"] == "pass"),
            "category_fail_count": sum(1 for item in categories.values() if item["status"] == "fail"),
            "category_not_applicable_count": sum(1 for item in categories.values() if item["status"] == "not_applicable"),
        },
        "next_route": next_route,
    }


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
    run_dir = Path(out_dir) if out_dir else root / ".driftlock" / "runs" / resolved_run_id
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
                    "layers": repo["driftlock_layers"],
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
        raise DriftlockError(f"Unknown runner state: {current}")
    key = (current, event)
    if key not in RUNNER_TRANSITIONS:
        raise DriftlockError(f"Invalid runner transition: {current} + {event}")
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


def fake_locked_spec() -> dict[str, Any]:
    return {
        "id": "dryrun-spec",
        "title": "Full-Skill Driftlock Dry Run",
        "status": "locked",
        "intent": "Build a local harness flow that proves Driftlock has separate first-class skills before implementation.",
        "product_shape": {
            "primary_user": "A non-developer product owner delegating long-horizon development to AI agents.",
            "first_screen": "A product-shape preview with first screen, primary flow, and decision card.",
            "core_flow": "Office Hours to UX Approval to Product Lock to gated execution.",
            "ux_principles": [
                "Show product shape before locking the spec.",
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
                "given": "The user has approved a UX preview.",
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
                "Review rejection routes through compound before returning to fixer.",
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
                "write_scope": ["scripts/driftlock.py", "templates"],
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
        "commands": [{"cmd": "driftlock dry-run build simulation", "status": status}],
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
                "owner": "compound",
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
        state = new_task_state(task, "dry-run", "dryrun-spec", Path(".driftlock/worktrees") / task["id"])
        for event in ("implementation-started", "implementation-ready", "build-pass", "reviewer-approve", "merge-pass"):
            state = apply_task_event(state, event, f"{task['id']} {event}")
        task_states.append(state)
    return build_execution_plan("dry-run", "dryrun-spec", Path(".driftlock/dry-run"), task_states)


def run_dry_run(out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    upstream_map = read_upstream_map(root)
    spec = fake_locked_spec()
    task_graph = fake_task_graph()
    build_evidence = fake_build_evidence("pass")
    rejected_review = fake_review_report("rejected")
    approved_review = fake_review_report("approved")
    amendment_request = fake_amendment_request()
    final_handoff = fake_final_handoff()
    ux_preview_html = "<!doctype html><html lang=\"en\"><title>Driftlock UX Preview</title><h1>UX Preview Approved</h1></html>\n"
    browser_evidence = build_browser_evidence(
        run_id="dry-run",
        mode="html",
        source="ux-preview.html",
        html_text=ux_preview_html,
        expected_text=["UX Preview Approved"],
        viewport_name="desktop",
    )
    proof_bundle = new_proof_bundle("dry-run", "pass")
    proof_bundle["artifacts"] = {
        "locked_spec": "locked-spec.json",
        "task_graph": "task-graph.json",
        "execution_plan": "execution-plan.json",
        "ux_guard": "ux-lock.md",
        "build_evidence": "build-evidence.json",
        "review_report": "review-report.json",
        "amendment_request": "amendment-request.json",
        "quality_report": "quality-report.json",
        "browser_evidence": "browser-evidence.json",
        "proof_bundle": "proof-bundle.json",
        "ce_synthesis": "ce-synthesis.json",
        "ce_brief": "ce-brief.md",
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
        {"skill": "driftlock-office-hours", "phase": "office-hours", "gate": "pass"},
        {"skill": "driftlock-brainstorm", "phase": "brainstorm", "gate": "pass"},
        {"skill": "driftlock-grill", "phase": "grill", "gate": "pass"},
        {"skill": "driftlock-intent-brief", "phase": "intent-brief", "gate": "pass"},
        {"skill": "driftlock-decision-classify", "phase": "decision-classify", "gate": "pass"},
        {"skill": "driftlock-decision-card", "phase": "decision-card", "gate": "pass"},
        {"skill": "driftlock-design-system-lite", "phase": "design-system-lite", "gate": "pass"},
        {"skill": "driftlock-ux-preview", "phase": "ux-preview", "gate": "pass"},
        {"skill": "driftlock-ux-approval", "phase": "ux-approval", "gate": "pass"},
        {"skill": "driftlock-product-lock", "phase": "product-lock", "gate": "pass"},
        {"skill": "driftlock-spec-gate", "phase": "spec-gate", "gate": "pass"},
        {"skill": "driftlock-task-split", "phase": "task-split", "gate": "pass"},
        {"skill": "driftlock-implementer", "phase": "implementer", "gate": "pass"},
        {"skill": "driftlock-builder", "phase": "builder", "gate": "fail", "route": "fixer"},
        {"skill": "driftlock-fixer", "phase": "fixer", "gate": "pass", "route": "builder"},
        {"skill": "driftlock-builder", "phase": "builder", "gate": "pass", "route": "reviewer"},
        {"skill": "driftlock-reviewer", "phase": "reviewer", "gate": "fail", "route": "compound"},
        {"skill": "driftlock-compound", "phase": "compound", "gate": "pass", "route": "fixer"},
        {"skill": "driftlock-fixer", "phase": "fixer", "gate": "pass", "route": "builder"},
        {"skill": "driftlock-builder", "phase": "builder", "gate": "pass", "route": "reviewer"},
        {"skill": "driftlock-reviewer", "phase": "reviewer", "gate": "pass", "route": "merge"},
        {"skill": "driftlock-builder", "phase": "merge", "gate": "pass", "route": "ux-guard"},
        {"skill": "driftlock-ux-guard", "phase": "ux-guard", "gate": "pass"},
        {"skill": "driftlock-amend-advisor", "phase": "amend-advisor", "gate": "needs-user"},
        {"skill": "driftlock-handoff", "phase": "quality-gate", "gate": "pass", "route": "proof"},
        {"skill": "driftlock-handoff", "phase": "proof-bundle", "gate": "pass", "route": "handoff"},
        {"skill": "driftlock-handoff", "phase": "handoff", "gate": "pass"},
    ]
    trace_skills = {step["skill"] for step in trace}
    missing_trace_skills = sorted(set(SKILLS) - trace_skills)
    if missing_trace_skills:
        raise DriftlockError(f"Dry-run trace missing skills: {', '.join(missing_trace_skills)}")

    write_text(out_dir / "office-hours.md", "# Office Hours\n\nDry-run office hours completed.\n")
    write_text(out_dir / "brainstorm-notes.md", "# Brainstorm Notes\n\nDry-run options explored.\n")
    write_text(out_dir / "intent-brief.md", "# Intent Brief\n\nDry-run intent brief completed.\n")
    write_json(out_dir / "decision-card.json", {"id": "DC1", "recommended": "Approve UX preview", "requires_user": True})
    write_text(out_dir / "design-system-lite.md", "# Design System Lite\n\nCompact, operational, evidence-first.\n")
    write_text(out_dir / "ux-preview.html", ux_preview_html)
    write_text(out_dir / "ux-lock.md", "# UX Lock\n\nApproved preview: ux-preview.html\n")
    spec_gate_report = build_spec_gate_report(
        spec,
        "# UX Lock\n\nApproved preview: ux-preview.html\n\nApproved by: dry-run\n",
        [{"status": "accepted", "decision": "approved", "source": "dry-run"}],
    )
    fail_if_errors(validate_spec_gate_report_obj(spec_gate_report))
    write_json(out_dir / "locked-spec.json", spec)
    write_json(out_dir / "spec-gate-report.json", spec_gate_report)
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
    init_execution_run(batch_smoke_graph, spec, batch_smoke_run, root, Path(".driftlock/worktrees"), "dry-run-batch")
    batch_smoke = dispatch_execution_batch(batch_smoke_run, "subagent", "locked-spec.json", "task-graph.json")
    fail_if_errors(validate_agent_dispatch_batch_obj(batch_smoke["batch"]))
    init_execution_run(task_graph, spec, out_dir, root, Path(".driftlock/worktrees"), "dry-run")
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
        ("T2", "ce-brief-ready", "T2 CE brief returned to fixer."),
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
        "# UX Lock\n\nApproved preview: ux-preview.html\n\nApproved by: dry-run\n",
        proof_bundle,
        browser_evidence,
        {
            "locked_spec": "locked-spec.json",
            "execution_plan": "execution-plan.json",
            "build_evidence": "build-evidence.json",
            "review_report": "review-report.json",
            "ux_lock": "ux-lock.md",
            "browser_evidence": "browser-evidence.json",
            "proof_bundle": "proof-bundle.json",
        },
    )
    fail_if_errors(validate_quality_report_obj(quality_report))
    ce_synthesis = build_ce_synthesis(
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
    fail_if_errors(validate_ce_synthesis_obj(ce_synthesis))
    write_json(out_dir / "build-evidence.json", build_evidence)
    write_json(out_dir / "review-rejected-report.json", rejected_review)
    write_json(out_dir / "review-report.json", approved_review)
    write_json(out_dir / "browser-evidence.json", browser_evidence)
    write_json(out_dir / "quality-report.json", quality_report)
    write_json(out_dir / "ce-synthesis.json", ce_synthesis)
    write_text(out_dir / "ce-brief.md", render_ce_brief(ce_synthesis))
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
                    "layers": repo["driftlock_layers"],
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
            "office-hours.md",
            "decision-card.json",
            "design-system-lite.md",
            "ux-preview.html",
            "ux-lock.md",
            "spec-gate-report.json",
            "task-graph.json",
            "execution-plan.json",
            "batch-smoke/dispatch/agent-dispatch-batch.json",
            "tasks/T1/state.json",
            "tasks/T2/state.json",
            "build-evidence.json",
            "review-rejected-report.json",
            "review-report.json",
            "browser-evidence.json",
            "quality-report.json",
            "ce-synthesis.json",
            "amendment-request.json",
            "ce-brief.md",
            "final-handoff.json",
            "proof-bundle.json",
            "upstream-sources.json",
            "state.json",
        ],
    }
    write_json(out_dir / "dry-run-summary.json", result)
    return result


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
        raise DriftlockError(f"Not a Git repository: {repo}")


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
            raise DriftlockError(f"Failed to create worktree for {item['task_id']}:\n{result.stderr.strip()}")


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
            "adapter": "driftlock-execution-loop",
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
        raise DriftlockError(f"No task states found in {tasks_dir}")
    states = []
    for state_file in sorted(tasks_dir.glob("*/state.json")):
        state = read_json(state_file)
        fail_if_errors(validate_task_state_obj(state))
        states.append(state)
    if not states:
        raise DriftlockError(f"No task states found in {tasks_dir}")
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
        raise DriftlockError(f"Invalid task transition: {task_state['task_id']} {current} + {event}")
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
    elif event == "ce-brief-ready":
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
        raise DriftlockError(f"Task {task_state['task_id']} is not dispatchable from state {state}")
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
        raise DriftlockError(f"Unknown execution dispatch mode: {mode}")
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
        f"You are the {route['role']} subagent for Driftlock task {task['task_id']}.",
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
        "Expected Driftlock events:",
        *[f"- {event}" for event in route["expected_events"]],
    ]
    if route.get("review_stages"):
        lines.extend(["", "Review stages:", *[f"- {stage}" for stage in route["review_stages"]]])
    lines.extend(["", "Preserve locked product intent. Route product-impacting ambiguity to driftlock-amend-advisor."])
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
        raise DriftlockError(f"Unknown execution dispatch mode: {mode}")
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


def check_removed_coarse_skills(skills_dir: Path) -> list[str]:
    errors = []
    for skill in REMOVED_COARSE_SKILLS:
        if (skills_dir / skill).exists():
            errors.append(f"old coarse skill still exists: {skill}")
    for skill in ("driftlock-product-lock", "driftlock-compound"):
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
    elif args.kind == "spec-gate-report":
        fail_if_errors(validate_spec_gate_report_obj(read_json(path)))
    elif args.kind == "browser-evidence":
        fail_if_errors(validate_browser_evidence_obj(read_json(path)))
    elif args.kind == "quality-report":
        fail_if_errors(validate_quality_report_obj(read_json(path)))
    elif args.kind == "ce-synthesis":
        fail_if_errors(validate_ce_synthesis_obj(read_json(path)))
    elif args.kind == "execution-plan":
        fail_if_errors(validate_execution_plan_obj(read_json(path)))
    elif args.kind == "task-state":
        fail_if_errors(validate_task_state_obj(read_json(path)))
    elif args.kind == "agent-dispatch":
        fail_if_errors(validate_agent_dispatch_obj(read_json(path)))
    elif args.kind == "agent-dispatch-batch":
        fail_if_errors(validate_agent_dispatch_batch_obj(read_json(path)))
    else:
        raise DriftlockError(f"Unknown validation kind: {args.kind}")
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
        raise DriftlockError(f"Spec gate failed; report written to {args.out}; next_route={report['next_route']}")
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
    ux_lock_path = artifact_path(run_dir, args.ux_lock, "ux-lock.md")
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
        raise DriftlockError(f"Quality gate failed; report written to {args.out}; next_route={report['next_route']}")
    return {"status": report["status"], "path": args.out, "next_route": report["next_route"], "metrics": report["metrics"]}


def command_browser_collect(args: argparse.Namespace) -> dict[str, Any]:
    target_count = sum(1 for target in (args.url, args.html, args.snapshot) if bool(target))
    if target_count != 1:
        raise DriftlockError("Provide exactly one browser target: --url, --html, or --snapshot")
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
            raise DriftlockError(f"HTML target not found: {html_path}") from exc
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
        raise DriftlockError(f"Browser evidence failed; report written to {args.out}")
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

    synthesis = build_ce_synthesis(
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
    fail_if_errors(validate_ce_synthesis_obj(synthesis))
    write_json(Path(args.out), synthesis)
    if args.brief_out:
        write_text(Path(args.brief_out), render_ce_brief(synthesis))
    if synthesis["status"] == "blocked" and not args.report_only:
        raise DriftlockError(f"CE synthesis blocked; report written to {args.out}; missing concrete failure trigger")
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
        ("compound blocks handoff-ready", {"runner_state": "COMPOUNDING"}, "handoff-ready"),
        ("amend advisor blocks auto-approve", {"runner_state": "AMENDMENT_PENDING"}, "auto-approve"),
    ]
    passed = []
    errors = []
    for name, state, event in checks:
        try:
            apply_runner_event(state, event, name)
        except DriftlockError:
            passed.append(name)
        else:
            errors.append(f"negative check failed: {name}")

    try:
        review_approved_runner = apply_runner_event({"runner_state": "REVIEWING"}, "reviewer-approve", "negative runner merge setup")
        if review_approved_runner.get("runner_state") == "MERGE_READY":
            passed.append("review approve routes to merge gate before handoff")
        else:
            errors.append("negative check failed: review approve did not route to merge gate")
    except DriftlockError as exc:
        errors.append(f"review approve merge route failed unexpectedly: {exc}")

    try:
        handoff_runner = {"runner_state": "REVIEWING", "history": []}
        for event in ("reviewer-approve", "merge-pass", "quality-pass", "proof-pass"):
            handoff_runner = apply_runner_event(handoff_runner, event, f"runner handoff path {event}")
        if handoff_runner.get("runner_state") == "HANDOFF_READY":
            passed.append("runner reaches handoff only after merge quality proof")
        else:
            errors.append("negative check failed: runner did not reach handoff after merge quality proof")
    except DriftlockError as exc:
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
        except DriftlockError as exc:
            errors.append(f"{name} produced an invalid report: {exc}")
            continue
        if report["status"] == "fail":
            passed.append(name)
        else:
            errors.append(f"negative check failed: {name}")

    fake_task = fake_task_graph()["tasks"][0]
    base_task_state = new_task_state(fake_task, "negative-run", "dryrun-spec", Path(".driftlock/worktrees/T1"))
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
        except DriftlockError:
            passed.append(name)
        else:
            errors.append(f"negative check failed: {name}")

    review_state = apply_task_event(base_task_state, "implementation-started", "negative review setup")
    review_state = apply_task_event(review_state, "implementation-ready", "negative review setup")
    review_state = apply_task_event(review_state, "build-pass", "negative review setup")
    review_dispatch = build_agent_dispatch(Path(".driftlock/negative"), review_state, "single-agent-fallback", "locked-spec.json", "task-graph.json")
    invalid_review_dispatch = json.loads(json.dumps(review_dispatch))
    invalid_review_dispatch["route"].pop("review_stages", None)
    try:
        fail_if_errors(validate_agent_dispatch_obj(invalid_review_dispatch))
    except DriftlockError:
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
    except DriftlockError as exc:
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
        except DriftlockError as exc:
            errors.append(f"batch dispatch negative setup failed: {exc}")

    quality_base_spec = fake_locked_spec()
    quality_base_plan = fake_done_execution_plan()
    quality_base_build = fake_build_evidence("pass")
    quality_base_review = fake_review_report("approved")
    quality_base_proof = new_proof_bundle("dry-run", "pass")
    quality_base_proof["artifacts"] = {
        "ux_guard": "ux-lock.md",
        "build_evidence": "build-evidence.json",
        "review_report": "review-report.json",
        "quality_report": "quality-report.json",
        "browser_evidence": "browser-evidence.json",
        "proof_bundle": "proof-bundle.json",
    }
    quality_base_browser = build_browser_evidence(
        run_id="negative-run",
        mode="html",
        source="negative-ux-preview.html",
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
        except DriftlockError as exc:
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
    except DriftlockError as exc:
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
    except DriftlockError as exc:
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
    except DriftlockError as exc:
        errors.append(f"failed browser quality produced invalid report: {exc}")
    no_trigger_ce = build_ce_synthesis("negative-run", quality_base_spec, quality_base_plan, quality_base_review, passing_quality, quality_base_build)
    try:
        fail_if_errors(validate_ce_synthesis_obj(no_trigger_ce))
        if no_trigger_ce["status"] == "blocked":
            passed.append("CE synthesis blocks missing trigger evidence")
        else:
            errors.append("negative check failed: CE synthesis blocks missing trigger evidence")
    except DriftlockError as exc:
        errors.append(f"CE missing trigger produced invalid report: {exc}")

    rejected_review = fake_review_report("rejected")
    ready_ce = build_ce_synthesis("negative-run", quality_base_spec, quality_base_plan, rejected_review, passing_quality, quality_base_build)
    invalid_handoff_ce = json.loads(json.dumps(ready_ce))
    invalid_handoff_ce["return_route"] = "driftlock-handoff"
    try:
        fail_if_errors(validate_ce_synthesis_obj(invalid_handoff_ce))
    except DriftlockError:
        passed.append("CE synthesis blocks direct handoff route")
    else:
        errors.append("negative check failed: CE synthesis blocks direct handoff route")

    invalid_amend_ce = json.loads(json.dumps(ready_ce))
    invalid_amend_ce["return_route"] = "driftlock-amend-advisor"
    invalid_amend_ce["intent_impact"]["amendment_required"] = False
    try:
        fail_if_errors(validate_ce_synthesis_obj(invalid_amend_ce))
    except DriftlockError:
        passed.append("CE synthesis blocks amendment route without amendment flag")
    else:
        errors.append("negative check failed: CE synthesis blocks amendment route without amendment flag")

    repeated_ce = build_ce_synthesis("negative-run", quality_base_spec, quality_base_plan, rejected_review, passing_quality, quality_base_build)
    repeated_ce["failure_clusters"].append(
        {
            "id": "CE-999",
            "kind": "repeated_failure",
            "severity": "high",
            "summary": "Repeated failure without learning note should be blocked.",
            "evidence": ["execution-plan.tasks.T1.attempts"],
            "owners": ["compound"],
        }
    )
    repeated_ce["learning_note"]["status"] = "not-needed"
    try:
        fail_if_errors(validate_ce_synthesis_obj(repeated_ce))
    except DriftlockError:
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Driftlock local harness helpers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate Driftlock JSON artifacts")
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
            "spec-gate-report",
            "browser-evidence",
            "quality-report",
            "ce-synthesis",
            "execution-plan",
            "task-state",
            "agent-dispatch",
            "agent-dispatch-batch",
        ],
    )
    validate.add_argument("path")
    validate.add_argument("--spec", help="Locked Spec path for task coverage validation")
    validate.set_defaults(func=command_validate)

    runner = subparsers.add_parser("runner-step", help="Apply a Driftlock runner transition")
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

    spec_gate = subparsers.add_parser("spec-gate", help="Run the Spec Kit based Driftlock spec gate adapter")
    spec_gate.add_argument("--spec", required=True, help="Locked Spec JSON path")
    spec_gate.add_argument("--out", required=True, help="Spec gate report JSON output path")
    spec_gate.add_argument("--ux-lock", help="UX lock markdown path")
    spec_gate.add_argument("--decision-log", help="Decision log JSONL path")
    spec_gate.add_argument("--report-only", action="store_true", help="Write the report but do not fail the command on gate failure")
    spec_gate.set_defaults(func=command_spec_gate)

    quality_gate = subparsers.add_parser("quality-gate", help="Run the gstack/CE based Driftlock Quality/QA adapter")
    quality_gate.add_argument("--run-dir", required=True, help="Run directory containing Driftlock artifacts")
    quality_gate.add_argument("--out", required=True, help="Quality report JSON output path")
    quality_gate.add_argument("--run-id")
    quality_gate.add_argument("--spec", help="Locked Spec JSON path, default: run-dir/locked-spec.json")
    quality_gate.add_argument("--execution-plan", help="Execution plan JSON path, default: run-dir/execution-plan.json")
    quality_gate.add_argument("--build", help="Build evidence JSON path, default: run-dir/build-evidence.json")
    quality_gate.add_argument("--review", help="Review report JSON path, default: run-dir/review-report.json")
    quality_gate.add_argument("--ux-lock", help="UX lock markdown path, default: run-dir/ux-lock.md")
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

    ce_synthesize = subparsers.add_parser("ce-synthesize", help="Synthesize repeated failure evidence into a CE fix brief")
    ce_synthesize.add_argument("--run-dir", required=True, help="Run directory containing Driftlock artifacts")
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

    init = subparsers.add_parser("init-run", help="Initialize a completeness-first Driftlock run record")
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
    worktree.add_argument("--worktrees", default=".driftlock/worktrees")
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
    execution_init.add_argument("--worktrees", default=".driftlock/worktrees")
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
    execution_start.add_argument("--worktrees", default=".driftlock/worktrees")
    execution_start.add_argument("--mode", choices=sorted(EXECUTION_DISPATCH_MODES), default="single-agent-fallback")
    execution_start.add_argument("--out")
    execution_start.set_defaults(func=command_execution_start)

    execution_next = subparsers.add_parser("execution-next", help="Show the next dependency-unblocked execution route")
    execution_next.add_argument("--run-dir", required=True)
    execution_next.set_defaults(func=command_execution_next)

    execution_dispatch = subparsers.add_parser(
        "execution-dispatch",
        help="Dispatch the next runnable task to the proper Driftlock role and write agent-dispatch.json",
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

    dry_run = subparsers.add_parser("dry-run", help="Run a deterministic Driftlock full-skill dry-run")
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
