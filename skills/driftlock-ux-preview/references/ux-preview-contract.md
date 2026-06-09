# Driftlock UX Preview Contract

## Purpose

Make product shape visible before agents write code.

## Upstream Contracts

- gstack: `third_party/upstream/gstack/design-html`
- gstack: `third_party/upstream/gstack/plan-design-review`
- Superpowers: `third_party/upstream/superpowers/skills/brainstorming`

UX preview is a pre-implementation artifact. It lets the user approve the
shape, density, first screen, workflow, and visual tone before product lock.

## Required Input

- `intent-brief.md`
- `decision-card.json`
- `design-system-lite.md`
- product constraints from office hours and grill

## Required Output

Produce `ux-preview.html` with enough evidence for the next Driftlock skill to continue without re-interrogating product intent.

## Gate Rules

- Preview is not production code.
- Do not skip preview for UI products.
- Do not lock spec until preview is approved.
- Do not hide major workflow changes in visual polish.
- If the preview reveals a product decision, route back to decision card before
  approval.

## Next Route

Route only to the next valid Driftlock skill or to `driftlock-amend-advisor` when product intent, UX lock, or spec meaning would change.
