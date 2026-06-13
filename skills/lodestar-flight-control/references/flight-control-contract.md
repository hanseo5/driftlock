# Lodestar Flight Control Contract

## Purpose

Approve or reject implementation from a read-only stance.

## Upstream Contracts

- Compound Engineering: `third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-code-review`
- Compound Engineering: `third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-code-review/references/findings-schema.json`
- Compound Engineering: `third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-code-review/references/persona-catalog.md`
- Compound Engineering: `third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-code-review/references/action-class-rubric.md`
- Superpowers: `third_party/upstream/superpowers/skills/requesting-code-review`
- Superpowers: `third_party/upstream/superpowers/skills/receiving-code-review`

Reviewer is read-only and may use multi-persona reasoning. Findings should be
structured enough for the runner to route to fixer, debrief, amendment advisor,
or handoff without interpreting prose.

## Required Input

- `locked-spec.json`
- `task-graph.json`
- `build-evidence.json`
- implementation diff or branch/worktree reference
- previous review findings if re-reviewing

## Required Output

Produce `review-report.json` with enough evidence for the next Lodestar skill to continue without re-interrogating product intent.

`quality-gate` consumes this artifact. Approved review reports must still
preserve read-only reviewer integrity: `reviewer_read_only: true` and
`code_edits_made: false`.

Reviewer output must include two ordered `review_stages`:

1. `spec-compliance-review`
2. `code-quality-review`

Code quality review cannot approve the task before spec compliance review has
approved it. If either stage rejects, route to fixer or amendment advisor.

Each finding should include:

- severity: `P0`, `P1`, `P2`, or `P3`
- category
- file and line when applicable
- summary
- evidence
- owner: `fixer`, `debrief`, `amend-advisor`, or `human`
- requires_verification boolean

The runner event sequence is:

- `reviewer-approve` marks the task `MERGE_READY`.
- `reviewer-reject` routes the task to fixer.
- `amendment-needed` routes the task to amendment advisor when the Locked Spec may be wrong.

## Gate Rules

- Reviewer must not edit code.
- Reviewer must not approve missing evidence.
- Reviewer must not skip the spec compliance stage.
- Reviewer integrity violations fail the Quality/QA adapter even if the report
  says `approved`.
- Review reject does not change product intent.
- If a finding implies the locked spec is wrong, route to
  `lodestar-course-correct` rather than silently widening scope.
- If the same class of failure repeats, route through `lodestar-debrief`
  before returning to fixer.

## Next Route

Route only to the next valid Lodestar skill or to `lodestar-course-correct` when product intent, UX lock, or spec meaning would change.
