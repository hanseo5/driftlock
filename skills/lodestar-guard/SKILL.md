---
name: lodestar-guard
description: Check implementation against the UX lock. Use during execution, review, integration, or handoff when implementation must be checked for drift from shape-lock.md and approved product-shape evidence.
---

# Lodestar Guard

Catch drift between approved product shape and delivered UI/UX.

## Workflow

1. Compare delivered product with shape-lock.md and preview evidence.
2. Classify differences as implementation miss or product amendment.
3. Route implementation misses to lodestar-eva.
4. Route product-shape changes to lodestar-course-correct.

## Rules

- Do not silently accept UX drift.
- Do not create new product intent.
- Handoff cannot pass while UX guard fails.

## Output

Produce `guard-report.json`. Read `references/guard-contract.md` for the exact contract.
