# Lodestar Shape Contract

## Purpose

Make product structure and final UI/UX visible before agents write code.

## Upstream Contracts

- gstack: `third_party/upstream/gstack/design-html`
- gstack: `third_party/upstream/gstack/plan-design-review`
- Superpowers: `third_party/upstream/superpowers/skills/brainstorming`

## Required Input

For the wireframe pass:

- `manifest.md`
- `call.json`
- product constraints from survey and shakedown

For the final UI/UX pass:

- approved `wireframe.html`
- approved `DESIGN.md`
- approved `design-preview.html`
- product constraints from survey and shakedown
- release-quality rubric from `references/release-quality-rubric.md`

## Required Output

- First pass: produce `wireframe.html` with enough evidence for the user to
  approve structure, flow, navigation, density, and first-screen priority.
- Final pass: produce `shape.html` with the approved `DESIGN.md` direction
  applied.
- Final pass must also produce `visual-qa.md` when a browser-rendered preview
  exists. It records screenshot path, release-quality failures found, fixes
  made, and final pass/fail status.
- Final pass must produce `responsive-matrix.json` for browser-rendered web
  previews. The matrix must cover mobile, tablet, and desktop before asking for
  final UI/UX approval.

## Gate Rules

- Previews are not production code.
- Do not skip wireframe preview for UI products.
- Do not skip final UI/UX preview for UI products.
- Do not lock the product until wireframe, design-system, and final UI/UX
  approvals are all recorded.
- Do not hide major workflow changes in visual polish.
- Do not ask for final UI/UX approval while the preview fails the release
  quality rubric.
- Do not accept generic card dashboards, placeholder data, awkward text
  wrapping in key controls, clipped content, non-semantic color, or platform
  mismatch as "good enough".
- Run a visual QA loop: open locally, capture or inspect a rendered screenshot,
  fix visible issues, and repeat until `visual-qa.md` records a pass.
- For web previews, run the matrix loop before final approval:
  `browser-collect --viewport mobile`, `--viewport tablet`, and
  `--viewport desktop`, then `responsive-matrix --require-screenshots`.
- Do not create fixed desktop-first structures that require emergency mobile
  patches. Start with a fluid/mobile-safe shell, then enhance tablet and
  desktop density.
- If either preview reveals a product decision, route back to decision card
  before approval.

## Next Route

Route from wireframe approval to `lodestar-palette`. Route from final UI/UX
approval to `lodestar-shape-lock`, or to `lodestar-course-correct` when product
intent, UX lock, or spec meaning would change.
