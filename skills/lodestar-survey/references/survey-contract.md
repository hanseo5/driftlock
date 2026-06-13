# Lodestar Survey Contract

## Purpose

Turn the user's raw request into a grounded product conversation.

## Upstream Contracts

- gstack: `third_party/upstream/gstack/office-hours`
- gstack: `third_party/upstream/gstack/plan-ceo-review`
- Superpowers: `third_party/upstream/superpowers/skills/brainstorming`

Use these as reference contracts, not directly exposed skills. Lodestar keeps
the user-facing surface small: ask only product-impacting questions, surface
recommendations through decision cards, and avoid implementation detail unless
it changes product shape.

## Required Input

- Raw user request
- Existing repo context, if a repo exists
- Any prior Lodestar run notes relevant to the same product
- `references/upstream-map.json`

## Required Output

Produce `survey.md` with enough evidence for the next Lodestar skill to continue without re-interrogating product intent.

The output must capture:

- product idea in one paragraph
- target user and urgent job-to-be-done
- narrowest useful wedge
- explicit non-goals or deferred scope
- decision questions that require user ownership
- recommendation for next Lodestar route

## Gate Rules

- Do not write implementation tasks.
- Do not lock product intent.
- Do not ask the user to decide mechanical implementation details.
- Do not expose upstream gstack or Superpowers commands as the product flow.
- Route visual/product-shape questions to `lodestar-shape` or
  `lodestar-call` instead of burying them in prose.

## Next Route

Route only to the next valid Lodestar skill or to `lodestar-course-correct` when product intent, UX lock, or spec meaning would change.
