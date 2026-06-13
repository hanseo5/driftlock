# Lodestar Quality Gate Contract

## Purpose

Convert build, review, UX, integration, and proof evidence into a deterministic
handoff blocker.

## Adapter Command

```powershell
python scripts/lodestar.py quality-gate --run-dir .lodestar/runs/<run-id> --out .lodestar/runs/<run-id>/quality-report.json
```

Collect browser evidence before final QA when the product has a renderable UI:

```powershell
python scripts/lodestar.py browser-collect --url http://127.0.0.1:3000 --expect-text "Approved surface text" --out .lodestar/runs/<run-id>/browser-evidence.json
```

If a real browser tool produced a rendered snapshot, use `--snapshot` instead
of raw URL/HTML so QA evaluates the hydrated page state.

Use `--report-only` for diagnosis. Without `--report-only`, a failing quality
gate exits non-zero and must not continue to handoff.

## Required Inputs

- `locked-spec.json`
- `execution-plan.json`
- `build-evidence.json`
- `review-report.json`
- `shape-lock.md`
- `browser-evidence.json`
- `proof-bundle.json`

## Required Output

Produce `quality-report.json`.

Required report fields:

- `run_id`
- `spec_id`
- `status`
- `upstream_source`
- `checks`
- `findings`
- `metrics`
- `next_route`
- `artifacts`

Required checks:

- execution completion
- build verification
- review integrity
- UX alignment
- acceptance coverage
- regression smoke
- integration readiness
- accessibility baseline
- proof readiness

Browser evidence contributes to UX alignment, regression smoke, and
accessibility baseline checks. Missing or failed browser evidence blocks final
handoff.

## Gate Rules

- Critical or high findings make the report fail.
- Passing quality reports route to `lodestar-dock`.
- Final handoff requires `browser-evidence.json` in the proof bundle artifacts.
- Failed implementation evidence routes to `lodestar-eva`.
- Repeated or systemic quality failure routes to `lodestar-debrief`.
- UX/spec/integration intent conflicts route to `lodestar-course-correct`.
- Final handoff requires `quality-report.json` in both the proof bundle and
  final handoff artifacts.
