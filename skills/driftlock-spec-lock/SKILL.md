---
name: driftlock-spec-lock
description: Lock product intent into an implementation-ready spec before code is written. Use when starting Driftlock, creating a product spec, clarifying ambiguous requirements, running brainstorming or grill-me before implementation, or deciding whether a spec is ready to hand off to long-horizon coding agents.
---

# Driftlock Spec Lock

Use this skill to turn product intent into a Locked Spec. Do not start implementation from a vague plan.

## Workflow

1. Capture the user's product intent, constraints, non-goals, risks, and target outcome.
2. Brainstorm options only long enough to expose important tradeoffs.
3. Run a grill-me pass one question at a time. Give a recommended answer with each question.
4. Resolve every product-impacting branch into explicit decisions.
5. Draft the spec with success criteria and acceptance scenarios.
6. Run the Spec Kit style gates: clarify, checklist, analyze, and coverage.
7. Lock the spec only when all gates pass and the user intent is stable.

## Rules

- Treat `grill-me` as mandatory before `status: locked`.
- Keep user intent owner approval separate from model recommendations.
- Make every success criterion testable.
- Include non-goals so execution agents know what not to build.
- If a real conflict appears after lock, route to `driftlock-amend`.

## Output

Produce a Locked Spec object matching `schemas/locked-spec.schema.json`. Prefer `templates/locked-spec.json` as the starting shape.

For the exact gate contract, read `references/spec-lock-contract.md`.
