# Lodestar Lock Contract

## Purpose

Convert approved intent and product shape into the Locked Spec contract.

## Upstream Contracts

- Spec Kit: `third_party/upstream/spec-kit/templates/commands/specify.md`
- Spec Kit: `third_party/upstream/spec-kit/templates/spec-template.md`
- Superpowers: `third_party/upstream/superpowers/skills/brainstorming`
- gstack: `third_party/upstream/gstack/plan-ceo-review`
- gstack: `third_party/upstream/gstack/plan-design-review`

Product lock is where approved survey, shakedown, decisions, wireframe,
design-system direction, and final UI/UX preview become an
implementation-facing spec. It must preserve the user's approved intent and
reject unresolved product-impacting ambiguity.

## Required Input

- `manifest.md`
- `decision-log.jsonl`
- `shape-lock.md`
- approved `wireframe.html`
- approved `DESIGN.md`
- approved `design-preview.html`
- approved `shape.html`
- passing `visual-qa.md`
- `references/upstream-map.json`

## Required Output

Produce `locked-spec.json` with enough evidence for the next Lodestar skill to
continue without re-interrogating product intent.

## Gate Rules

- Do not run without wireframe, design-system, visual QA, and final UI/UX
  approval.
- Do not preserve old spec-lock compatibility behavior.
- Locked Spec must remain testable.
- Do not convert advisor recommendations into user approval.
- Do not accept vague success criteria that cannot be tested.

## Next Route

Route only to the next valid Lodestar skill or to `lodestar-course-correct`
when product intent, UX lock, or spec meaning would change.
