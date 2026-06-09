---
name: driftlock-ux-guard
description: Check implementation against the UX lock. Use during execution, review, integration, or handoff when implementation must be checked for drift from ux-lock.md and approved product-shape evidence.
---

# Driftlock UX Guard

Catch drift between approved product shape and delivered UI/UX.

## Workflow

1. Compare delivered product with ux-lock.md and preview evidence.
2. Classify differences as implementation miss or product amendment.
3. Route implementation misses to fixer.
4. Route product-shape changes to amend advisor.

## Rules

- Do not silently accept UX drift.
- Do not create new product intent.
- Handoff cannot pass while UX guard fails.

## Output

Produce `ux-guard-report.json`. Read `references/ux-guard-contract.md` for the exact contract.
