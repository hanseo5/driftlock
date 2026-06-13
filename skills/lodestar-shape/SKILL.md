---
name: lodestar-shape
description: Show the product shape before spec lock. Use when the user must see the first useful screen, core flow, navigation model, or interaction feel before Lodestar locks the product spec.
---

# Lodestar Shape

Make product shape visible before agents write code.

## Workflow

1. Render a lightweight UX preview, usually HTML for browser review.
2. Show first screen, primary flow, decision surfaces, and density.
3. Use palette.md as constraints.
4. Route to lodestar-shape-lock.

## Rules

- Preview is not production code.
- Do not skip preview for UI products.
- Do not lock spec until preview is approved.

## Output

Produce `shape.html`. Read `references/shape-contract.md` for the exact contract.
