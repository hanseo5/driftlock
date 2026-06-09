# Driftlock Fixer Contract

## Purpose

Own code changes after failure feedback.

## Required Input

Use the upstream Driftlock artifacts and evidence required by this workflow step. If the required upstream artifact is missing, stop and route backward rather than guessing.

## Required Output

Produce `fix-handoff.json` with enough evidence for the next Driftlock skill to continue without re-interrogating product intent.

The runner event sequence is:

- `fix-ready` returns to implementer before builder/reviewer.
- `ce-needed` activates compound mode for repeated or unclear failures.
- `amendment-needed` routes spec/product conflicts to amendment advisor.

## Gate Rules

- Do not bypass builder.
- Do not broaden scope silently.
- Route spec or product conflicts to amend advisor.

## Next Route

Route only to the next valid Driftlock skill or to `driftlock-amend-advisor` when product intent, UX lock, or spec meaning would change.
