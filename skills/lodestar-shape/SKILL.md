---
name: lodestar-shape
description: Show product shape before implementation. Use first for a wireframe preview, then again after design-system approval for the final UI/UX preview before Lodestar locks the product.
---

# Lodestar Shape

Make product structure and final UI/UX visible before agents write code.

## Workflow

1. First pass: render `wireframe.html` for structure, first screen, primary
   flow, navigation, density, and decision surfaces.
2. Open `wireframe.html` in the local browser immediately and stop for
   structure/flow approval.
3. Route approved wireframe decisions to `lodestar-palette`.
4. Second pass: after `DESIGN.md` is approved, render `shape.html` as the final
   UI/UX preview using the approved design-system constraints.
5. Run the release-quality responsive QA loop: collect mobile, tablet, and
   desktop evidence, write `responsive-matrix.json`, inspect screenshots when
   possible, fix visible issues, and write `visual-qa.md`.
6. Open `shape.html` in the local browser immediately and stop for final UI/UX
   approval only after responsive matrix and visual QA pass.
7. Route to `lodestar-shape-lock`.

## Rules

- Preview is not production code.
- Do not skip wireframe preview for UI products.
- Do not skip final UI/UX preview for UI products.
- Do not lock the product until both the wireframe and final UI/UX preview are
  approved.
- Do not present a rough MVP, generic dashboard, placeholder content, or
  visibly broken layout as final UI/UX.
- Never ask a non-developer to open a file path manually when local browser
  launch is available.

## Output

Produce `wireframe.html` for the first pass and `shape.html` plus
`responsive-matrix.json` plus `visual-qa.md` for the final pass. Read
`references/shape-contract.md` for the exact contract.
