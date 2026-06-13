"""Shared constants: skill names, phases, gates, runner states, transitions."""
from __future__ import annotations


SKILLS = (
    "lodestar-survey",
    "lodestar-scout",
    "lodestar-shakedown",
    "lodestar-manifest",
    "lodestar-triage",
    "lodestar-call",
    "lodestar-palette",
    "lodestar-shape",
    "lodestar-shape-lock",
    "lodestar-guard",
    "lodestar-lock",
    "lodestar-checklist",
    "lodestar-stages",
    "lodestar-engineer",
    "lodestar-integrator",
    "lodestar-flight-control",
    "lodestar-eva",
    "lodestar-course-correct",
    "lodestar-debrief",
    "lodestar-dock",
)

REMOVED_COARSE_SKILLS = {
    "lodestar-spec-lock",
    "lodestar-execute",
    "lodestar-amend",
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
    "debrief",
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
CE_RETURN_ROUTES = {"lodestar-eva", "lodestar-engineer", "lodestar-course-correct"}
CE_FORBIDDEN_ROUTES = {"lodestar-flight-control", "lodestar-dock"}
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
    ("COMPOUNDING", "debrief-brief-ready"): "FIXING",
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
    ("COMPOUNDING", "debrief-brief-ready"): ("FIXING", "in-progress", None),
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
        "skill": "lodestar-engineer",
        "mutates_code": True,
        "next_step": "make scoped code changes using TDD and produce implementation-handoff.json",
        "output_artifact": "implementation-handoff.json",
        "expected_events": ["implementation-ready", "implementation-blocked"],
    },
    "BUILDING": {
        "role": "builder",
        "skill": "lodestar-integrator",
        "mutates_code": False,
        "next_step": "run build, lint, tests, smoke checks, and produce build-evidence.json",
        "output_artifact": "build-evidence.json",
        "expected_events": ["build-pass", "build-fail"],
    },
    "REVIEWING": {
        "role": "reviewer",
        "skill": "lodestar-flight-control",
        "mutates_code": False,
        "next_step": "perform two-stage read-only spec compliance and code quality review, then produce review-report.json",
        "output_artifact": "review-report.json",
        "expected_events": ["reviewer-approve", "reviewer-reject", "amendment-needed"],
        "review_stages": list(REVIEW_STAGES),
    },
    "MERGE_READY": {
        "role": "integrator",
        "skill": "lodestar-integrator",
        "mutates_code": True,
        "next_step": "merge or integrate the reviewed task branch and produce merge-evidence.json",
        "output_artifact": "merge-evidence.json",
        "expected_events": ["merge-pass", "merge-conflict", "ce-needed"],
    },
    "FIXING": {
        "role": "fixer",
        "skill": "lodestar-eva",
        "mutates_code": True,
        "next_step": "fix rejected or failed work and produce fix-handoff.json",
        "output_artifact": "fix-handoff.json",
        "expected_events": ["fix-ready", "ce-needed", "amendment-needed"],
    },
    "COMPOUNDING": {
        "role": "debrief",
        "skill": "lodestar-debrief",
        "mutates_code": False,
        "next_step": "synthesize repeated failure learning and route back to fixer or implementer",
        "output_artifact": "debrief.json",
        "expected_events": ["debrief-brief-ready"],
    },
    "AMENDMENT_PENDING": {
        "role": "amend-advisor",
        "skill": "lodestar-course-correct",
        "mutates_code": False,
        "next_step": "advise on product-impacting amendment without auto-approving user intent",
        "output_artifact": "amendment-request.json",
        "expected_events": ["amendment-approved"],
    },
}
