# Driftlock UX Guard Contract

## Purpose

Catch drift between approved product shape and delivered UI/UX.

## Upstream Contracts

- gstack: `third_party/upstream/gstack/design-review`
- gstack: `third_party/upstream/gstack/guard`
- Compound Engineering: `third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-proof`

UX guard compares implementation evidence against the approved UX lock. It is
not a taste review from scratch; it is drift detection against approved product
shape.

## Required Input

- `ux-lock.md`
- approved `ux-preview.html`
- implementation evidence or browser screenshot
- `browser-evidence.json` when a browser-rendered surface exists
- `build-evidence.json`
- `review-report.json`

## Required Output

Produce `ux-guard-report.json` with enough evidence for the next Driftlock skill to continue without re-interrogating product intent.

The Quality/QA adapter also reads `ux-lock.md` and product-shape approval
evidence. Missing UX lock or browser evidence fails QA and blocks handoff.

## Gate Rules

- Do not silently accept UX drift.
- Do not create new product intent.
- Handoff cannot pass while UX guard fails.
- QA cannot pass while UX lock, approved preview evidence, or browser evidence
  is missing.
- Browser evidence must be refreshed after implementation or fixer changes that
  can affect the rendered UI.
- If a drift is product-improving but intent-changing, route to
  `driftlock-amend-advisor`.
- If a drift is accidental, route to `driftlock-fixer`.

## Next Route

Route only to the next valid Driftlock skill or to `driftlock-amend-advisor` when product intent, UX lock, or spec meaning would change.
