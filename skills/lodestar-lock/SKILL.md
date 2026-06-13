---
name: lodestar-lock
description: Create the Locked Spec after wireframe, design-system, and final UI/UX approval.
---

# Lodestar Lock

Convert approved intent and product shape into the Locked Spec contract.

## Workflow

1. Verify required upstream artifacts exist.
2. Verify wireframe approval, design-system approval, and final UI/UX approval
   are recorded in `shape-lock.md`.
3. Write `product_shape` with `approved_preview` true.
4. Record all product-impacting decisions and gate evidence.
5. Output `locked-spec.json` and route to the checklist gate.

## Rules

- Do not run without wireframe, design-system, and final UI/UX approval.
- Do not route through the removed spec-lock entrypoint.
- Locked Spec must remain testable.

## Output

Produce `locked-spec.json`. Read `references/lock-contract.md` for the exact
contract.
