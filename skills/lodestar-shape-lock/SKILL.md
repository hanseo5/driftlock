---
name: lodestar-shape-lock
description: Capture approval of the wireframe, approved design system, and final UI/UX preview before product lock.
---

# Lodestar Shape Lock

Make wireframe, design-system, and final UI/UX approval explicit gates before
product lock.

## Workflow

1. Confirm the wireframe structure and flow were approved.
2. Confirm the design-system direction was approved.
3. Ask whether the final UI/UX preview matches the intended product.
4. Record approved first screen, flow, density, design-system rules, and
   must-not-drift rules.
5. Write `shape-lock.md` when approved.
6. Return to wireframe, design-system, or final UI/UX preview when rejected.

## Rules

- User approval is required.
- Advisors cannot approve product shape.
- Approved wireframe, design-system direction, and final UI/UX preview must be
  referenced by product lock.

## Output

Produce `shape-lock.md`. Read `references/shape-lock-contract.md` for the exact
contract.
