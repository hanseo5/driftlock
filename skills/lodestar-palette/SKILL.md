---
name: lodestar-palette
description: Present design-system choices after wireframe approval and produce DESIGN.md before final UI/UX preview.
---

# Lodestar Palette

Create a usable AI-readable design system after the user has approved the
wireframe structure. The goal is not a vague palette; it is a `DESIGN.md` that
can guide agents toward consistent, release-quality UI.

## Workflow

1. Use the approved wireframe as the structural constraint.
2. Present 2-3 plain-language design-system directions with a recommendation.
3. After approval, produce `DESIGN.md` with product archetype, benchmark bar,
   visual theme, color roles, typography, components/states, layout rules,
   elevation/depth, data realism rules, release-quality acceptance criteria,
   do/don't rules, mobile/tablet/desktop responsive behavior, 320px reflow,
   component adaptation rules, and agent prompt guidance.
4. Produce `design-preview.html` as a small visual catalog of the design system
   and open it locally when available.
5. Stop for explicit design-system approval.
6. Optionally output `palette.md` as a compatibility summary, but `DESIGN.md`
   is the source of truth.

## Rules

- Do not create a marketing landing page unless requested.
- Do not leave design direction at the level of mood words.
- Do not skip benchmark references or release-quality acceptance criteria.
- Preserve user-approved wireframe structure, density, and first-screen
  expectations.
- Do not move to final UI/UX preview until the design-system direction is
  approved.
- The final UI/UX preview must visibly follow `DESIGN.md`.

## Output

Produce `DESIGN.md` and `design-preview.html`. Read
`references/palette-contract.md` for the exact contract.
