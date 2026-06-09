---
name: driftlock-product-lock
description: Create the Locked Spec after UX approval. Use only after intent brief, decision policy, design-system-lite, UX preview, and UX approval exist and product intent is ready to become a Locked Spec.
---

# Driftlock Product Lock

Convert approved intent and product shape into the Locked Spec contract.

## Workflow

1. Verify required upstream artifacts exist.
2. Write product_shape with approved_preview true.
3. Record all product-impacting decisions and gate evidence.
4. Output locked-spec.json and route to spec gate.

## Rules

- Do not run without UX approval.
- Do not route through the removed spec-lock entrypoint.
- Locked Spec must remain testable.

## Output

Produce `locked-spec.json`. Read `references/product-lock-contract.md` for the exact contract.
