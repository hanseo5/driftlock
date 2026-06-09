# Driftlock Compound Contract

## Purpose

Create root-cause learning and a fix brief without skipping execution gates.

## Upstream Contracts

- Compound Engineering: `third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-compound`
- Compound Engineering: `third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-compound-refresh`
- Compound Engineering: `third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-debug`
- Compound Engineering: `third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-compound/references/schema.yaml`
- gstack: `third_party/upstream/gstack/learn`
- gstack: `third_party/upstream/gstack/context-save`
- gstack: `third_party/upstream/gstack/context-restore`

Compound mode is a learning and route-repair engine. It documents the repeated
failure pattern, extracts the fix hypothesis, and returns execution to the
mutation owner. It does not become a shortcut around builder or reviewer.

## Required Input

- failing build evidence, rejected review, or repeated fixer loop
- current locked spec and task graph
- run history from `.driftlock/runs/<run-id>/state.json`
- prior learning notes if available

## Required Output

Produce `ce-synthesis.json` and `ce-brief.md` with enough evidence for the next Driftlock skill to continue without re-interrogating product intent.

The adapter command is:

```powershell
python scripts/driftlock.py ce-synthesize --run-dir .driftlock/runs/<run-id> --out .driftlock/runs/<run-id>/ce-synthesis.json --brief-out .driftlock/runs/<run-id>/ce-brief.md
```

The synthesis JSON must include:

- triggering failure
- failure clusters
- root-cause hypothesis
- what did not work
- next fix strategy
- verification plan
- learning note status and prevention rule
- whether product intent might be affected
- return route: `driftlock-fixer`, `driftlock-implementer`, or
  `driftlock-amend-advisor`
- forbidden routes: `driftlock-reviewer`, `driftlock-handoff`

The Markdown brief is a human-readable rendering of `ce-synthesis.json`.

## Gate Rules

- CE is conditional, not always on.
- CE does not edit code directly.
- CE must return through fixer/implementer and builder.
- CE must not hand off directly.
- CE must not route directly to reviewer.
- CE must write or update learning artifacts when a repeated failure pattern is
  confirmed.

## Next Route

Route only to the next valid Driftlock skill or to `driftlock-amend-advisor` when product intent, UX lock, or spec meaning would change.
