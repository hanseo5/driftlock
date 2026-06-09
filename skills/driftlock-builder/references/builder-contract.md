# Driftlock Builder Contract

## Purpose

Verify the implementation mechanically before review.

## Upstream Contracts

- Superpowers: `third_party/upstream/superpowers/skills/verification-before-completion`
- Superpowers: `third_party/upstream/superpowers/skills/test-driven-development`
- Compound Engineering: `third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-test-browser`
- Compound Engineering: `third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-proof`
- gstack: `third_party/upstream/gstack/qa`
- gstack: `third_party/upstream/gstack/qa-only`

Builder is the evidence owner. It may run commands, tests, app/browser checks,
and proof collection. It must not approve code quality; that is reviewer scope.

## Required Input

Use the upstream Driftlock artifacts and evidence required by this workflow step. If the required upstream artifact is missing, stop and route backward rather than guessing.

## Required Output

Produce `build-evidence.json` and, when the product has a browser-rendered
surface, `browser-evidence.json` with enough evidence for the next Driftlock
skill to continue without re-interrogating product intent.

`quality-gate` consumes this artifact. Include concrete command entries with
`cmd` and `status`, and make sure at least one meaningful smoke command is
recorded when the product has a runnable surface.

Use the browser collector when there is an HTML preview, local app URL, or other
renderable target:

```powershell
python scripts/driftlock.py browser-collect --url http://127.0.0.1:3000 --expect-text "Approved surface text" --out .driftlock/runs/<run-id>/browser-evidence.json
```

When Playwright, Codex Browser, or another real browser tool has already
captured rendered DOM, console, and screenshot evidence, pass that handoff as a
snapshot:

```powershell
python scripts/driftlock.py browser-collect --snapshot .driftlock/runs/<run-id>/browser-snapshot.json --expect-text "Approved surface text" --out .driftlock/runs/<run-id>/browser-evidence.json
```

The runner event sequence is:

- `build-pass` routes the task to reviewer.
- `build-fail` routes the task to fixer.

## Gate Rules

- Builder may diagnose but does not silently rewrite implementation.
- Build pass is required before normal review.
- Evidence must be concrete.
- Build evidence must be strong enough for the Quality/QA adapter to evaluate
  regression smoke.
- Browser evidence is required before final QA when the product has a rendered
  UI surface.
- If build or QA fails, route to `driftlock-fixer`.
- If browser/design evidence is required by the product shape, refresh
  `browser-evidence.json` or route to `driftlock-ux-guard`.

## Next Route

Route only to the next valid Driftlock skill or to `driftlock-amend-advisor` when product intent, UX lock, or spec meaning would change.
