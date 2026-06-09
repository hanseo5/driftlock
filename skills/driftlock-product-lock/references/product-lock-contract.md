# Driftlock Product Lock Contract

## Purpose

Convert approved intent and product shape into the Locked Spec contract.

## Upstream Contracts

- Spec Kit: `third_party/upstream/spec-kit/templates/commands/specify.md`
- Spec Kit: `third_party/upstream/spec-kit/templates/spec-template.md`
- Superpowers: `third_party/upstream/superpowers/skills/brainstorming`
- gstack: `third_party/upstream/gstack/plan-ceo-review`
- gstack: `third_party/upstream/gstack/plan-design-review`

Product lock is where approved office-hours, grill, decisions, and UX preview
become an implementation-facing spec. It must preserve the user's approved
intent and reject unresolved product-impacting ambiguity.

## Required Input

- `intent-brief.md`
- `decision-log.jsonl`
- `ux-lock.md`
- approved `ux-preview.html`
- `references/upstream-map.json`

## Required Output

Produce `locked-spec.json` with enough evidence for the next Driftlock skill to continue without re-interrogating product intent.

## Gate Rules

- Do not run without UX approval.
- Do not preserve old spec-lock compatibility behavior.
- Locked Spec must remain testable.
- Do not convert advisor recommendations into user approval.
- Do not accept vague success criteria that cannot be tested.

## Next Route

Route only to the next valid Driftlock skill or to `driftlock-amend-advisor` when product intent, UX lock, or spec meaning would change.
