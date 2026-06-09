---
name: driftlock-spec-gate
description: Validate the Locked Spec before task split. Use after product lock to run clarify, checklist, analyze, coverage, and testability gates before tasks are created.
---

# Driftlock Spec Gate

Block weak specs before execution agents receive work.

## Workflow

1. Validate product shape, decisions, success criteria, scenarios, and gates.
2. List missing or contradictory requirements.
3. Produce spec-gate-report.json.
4. Route failures to product lock or amend advisor.

## Rules

- Do not create tasks from a failing spec.
- Do not downgrade product-shape approval requirements.
- Do not hide spec conflicts.

## Output

Produce `spec-gate-report.json`. Read `references/spec-gate-contract.md` for the exact contract.
