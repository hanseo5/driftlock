---
name: lodestar-checklist
description: Validate the Locked Spec before task split. Use after product lock to run clarify, checklist, analyze, coverage, and testability gates before tasks are created.
---

# Lodestar Checklist

Block weak specs before execution agents receive work.

## Workflow

1. Validate product shape, decisions, success criteria, scenarios, and gates.
2. List missing or contradictory requirements.
3. Produce checklist-report.json.
4. Route failures to product lock or amend advisor.

## Rules

- Do not create tasks from a failing spec.
- Do not downgrade wireframe, design-system, or final UI/UX approval requirements.
- Do not hide spec conflicts.

## Output

Produce `checklist-report.json`. Read `references/checklist-contract.md` for the exact contract.
