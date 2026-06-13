# Lodestar Shape Lock Contract

## Purpose

Make wireframe, design-system, and final UI/UX approval explicit gates before
product lock.

## Required Input

- approved `wireframe.html`
- approved `DESIGN.md`
- approved `design-preview.html`
- approved `shape.html`
- passing `visual-qa.md`
- passing `responsive-matrix.json` for browser-rendered web previews
- approval evidence from the user or Express-mode approval log where allowed

If required upstream artifacts are missing, stop and route backward rather than
guessing.

## Required Output

Produce `shape-lock.md` with enough evidence for the next Lodestar skill to
continue without re-interrogating product intent.

`shape-lock.md` must record:

- approved wireframe structure and flow
- approved design-system direction
- approved final UI/UX preview
- first-screen priority
- layout density
- mobile/tablet/desktop responsive matrix result
- must-not-drift rules
- rejected alternatives or scope warnings, if any

## Gate Rules

- User approval is required for final UI/UX approval.
- Advisors cannot approve product shape.
- Approved wireframe, design-system direction, and final UI/UX preview must be
  referenced by product lock.
- Final UI/UX approval must not be recorded if visual QA failed or is missing
  for a browser-rendered UI product.
- Final UI/UX approval for web previews must not be recorded if the responsive
  matrix is missing or failing.

## Next Route

Route only to the next valid Lodestar skill or to `lodestar-course-correct`
when product intent, UX lock, or spec meaning would change.
