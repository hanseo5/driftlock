# Lodestar Palette Contract

## Purpose

Create enough AI-readable design-system direction to stop implementation from
producing the wrong kind of interface.

## Required Input

- approved `wireframe.html`
- product constraints from survey and shakedown
- relevant product decisions from `call.json`

If required upstream artifacts are missing, stop and route backward rather than
guessing.

## Required Output

Produce `DESIGN.md` with enough evidence for the next Lodestar skill to render
the final UI/UX preview without re-interrogating product intent.

`DESIGN.md` must include:

- product archetype and platform target
- benchmark bar with 2-3 named reference products or design systems
- visual theme and atmosphere
- color palette and semantic roles
- typography rules and hierarchy
- component inventory, styling, states, and interaction expectations
- layout principles and spacing scale
- responsive contract: mobile, tablet, and desktop viewport matrix, 320 CSS px
  reflow rule, content priority per viewport, and component adaptation rules
- depth and elevation rules
- data realism rules for sample content and metrics
- release-quality acceptance criteria
- visual QA checklist for the final `shape.html`
- do's and don'ts
- responsive behavior that names mobile, tablet, and desktop explicitly
- agent prompt guide
- explicit user approval or recommended Express-mode approval log

Also produce `design-preview.html`, a visual catalog showing enough of the
tokens and components for the user to approve the direction. `palette.md` may be
produced as a compatibility summary, but `DESIGN.md` is the source of truth.

## Gate Rules

- Do not create a marketing landing page unless requested.
- Do not leave design direction at the level of mood words.
- Do not produce `DESIGN.md` without a product archetype, benchmark bar,
  release-quality acceptance criteria, and anti-slop constraints.
- Do not describe responsiveness only as "works on mobile"; define the
  component behavior for mobile, tablet, and desktop before final preview.
- Preserve user-approved wireframe structure, density, and first-screen
  expectations.
- Do not move to final UI/UX preview until design-system direction is approved.
- The final UI/UX preview must visibly follow `DESIGN.md`.
- If `design-preview.html` looks like a mood board instead of a component
  catalog with states and real sample data, reject it and regenerate.
- Use `references/release-quality-rubric.md` as the minimum design bar.

## Next Route

Route to `lodestar-shape` for final UI/UX preview, or to
`lodestar-course-correct` when product intent, UX lock, or spec meaning would
change.
