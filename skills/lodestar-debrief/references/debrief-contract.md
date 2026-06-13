# Lodestar Debrief Contract

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

Debrief mode is a learning and route-repair engine. It documents the repeated
failure pattern, extracts the fix hypothesis, and returns execution to the
mutation owner. It does not become a shortcut around builder or reviewer.

## Required Input

- failing build evidence, rejected review, or repeated fixer loop
- current locked spec and task graph
- run history from `.lodestar/runs/<run-id>/state.json`
- prior learning notes if available

## Required Output

Produce `debrief.json` and `debrief-brief.md` with enough evidence for the next Lodestar skill to continue without re-interrogating product intent.

The adapter command is:

```powershell
python scripts/lodestar.py ce-synthesize --run-dir .lodestar/runs/<run-id> --out .lodestar/runs/<run-id>/debrief.json --brief-out .lodestar/runs/<run-id>/debrief-brief.md
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
- return route: `lodestar-eva`, `lodestar-engineer`, or
  `lodestar-course-correct`
- forbidden routes: `lodestar-flight-control`, `lodestar-dock`

The Markdown brief is a human-readable rendering of `debrief.json`.

## Gate Rules

- Debrief is conditional, not always on.
- Debrief does not edit code directly.
- Debrief must return through fixer/implementer and builder.
- Debrief must not hand off directly.
- Debrief must not route directly to reviewer.
- Debrief must write or update learning artifacts when a repeated failure pattern is
  confirmed.

## Next Route

Route only to the next valid Lodestar skill or to `lodestar-course-correct` when product intent, UX lock, or spec meaning would change.
