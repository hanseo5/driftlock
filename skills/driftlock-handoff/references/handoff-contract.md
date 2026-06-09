# Driftlock Handoff Contract

## Purpose

Produce final delivery evidence without hiding remaining risk.

## Upstream Contracts

- gstack: `third_party/upstream/gstack/ship`
- gstack: `third_party/upstream/gstack/guard`
- gstack: `third_party/upstream/gstack/health`
- Superpowers: `third_party/upstream/superpowers/skills/finishing-a-development-branch`
- Superpowers: `third_party/upstream/superpowers/skills/verification-before-completion`
- Compound Engineering: `third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-proof`
- Quality Gate: `references/quality-gate-contract.md`

Handoff is proof-bundle delivery. It should summarize what changed, what was
verified, what remains risky, and why the result is ready.

## Required Input

Use the upstream Driftlock artifacts and evidence required by this workflow step. If the required upstream artifact is missing, stop and route backward rather than guessing.

## Required Output

Produce `final-handoff.json` with enough evidence for the next Driftlock skill to continue without re-interrogating product intent.

The handoff artifact must include:

- all proof bundle gates as `pass`
- `artifacts.proof_bundle`
- `artifacts.quality_report`

## Gate Rules

- Do not hand off with failing or missing gates.
- Do not treat advisor recommendation as user approval.
- Do not omit evidence.
- Do not hand off without QA/proof evidence for the user-facing surface.
- Do not hand off without a passing `quality-report.json`.
- Do not hand off until every task has passed review, merge/integration, and QA.
- Do not hand off directly after CE; the route must return through fixer or
  implementer, builder, reviewer, UX guard, then handoff.
- Do not hand off directly after reviewer approval. Reviewer approval routes to
  the merge/integration gate, then QA/quality, then proof, then handoff.

## Next Route

Route only to the next valid Driftlock skill or to `driftlock-amend-advisor` when product intent, UX lock, or spec meaning would change.
