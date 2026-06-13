# Lodestar Checklist Contract

## Purpose

Block weak specs before execution agents receive work.

## Upstream Contracts

- Spec Kit: `third_party/upstream/spec-kit/templates/commands/clarify.md`
- Spec Kit: `third_party/upstream/spec-kit/templates/commands/analyze.md`
- Spec Kit: `third_party/upstream/spec-kit/templates/commands/specify.md`
- Spec Kit: `third_party/upstream/spec-kit/templates/commands/plan.md`
- Spec Kit: `third_party/upstream/spec-kit/templates/spec-template.md`
- Spec Kit: `third_party/upstream/spec-kit/templates/plan-template.md`
- Spec Kit: `third_party/upstream/spec-kit/templates/checklist-template.md`

Use these to enforce ambiguity coverage, implementation readiness, and
testability before task split. The Spec Kit command files are upstream
reference contracts; Lodestar owns the resulting `checklist-report.json`.

## Required Input

- `locked-spec.json`
- `shape-lock.md`
- `decision-log.jsonl`
- `references/upstream-map.json`

## Required Output

Produce `checklist-report.json` with enough evidence for the next Lodestar skill to continue without re-interrogating product intent.

The deterministic local adapter command is:

```powershell
lodestar.py spec-gate --spec locked-spec.json --ux-lock shape-lock.md --decision-log decision-log.jsonl --out checklist-report.json
```

Default behavior writes the report and exits non-zero when the gate fails.
`--report-only` may be used for diagnosis without blocking the shell command.

The report shape must include:

- `spec_id`
- `status`: `pass` or `fail`
- `upstream_source`
- `categories`
- `findings`
- `metrics`
- `next_route`

The report must score at least:

- functional scope
- data model
- UX flow
- non-functional quality
- integrations
- edge and failure handling
- constraints and tradeoffs
- terminology
- completion signals
- placeholders

## Gate Rules

- Do not create tasks from a failing spec.
- Do not downgrade product-shape approval requirements.
- Do not hide spec conflicts.
- Do not treat unanswered product-impacting questions as engineering choices.
- `critical` or `high` findings make the report fail.
- A passing report must route to `lodestar-stages`.
- If a spec conflict changes product intent, route to
  `lodestar-course-correct` and require user approval.

## Next Route

Route only to the next valid Lodestar skill or to `lodestar-course-correct` when product intent, UX lock, or spec meaning would change.
