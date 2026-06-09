# Driftlock Amend Advisor Contract

## Purpose

Translate spec conflicts into user-decidable product options.

## Required Input

Use the upstream Driftlock artifacts and evidence required by this workflow step. If the required upstream artifact is missing, stop and route backward rather than guessing.

## Required Output

Produce `amendment-request.json` with enough evidence for the next Driftlock skill to continue without re-interrogating product intent.

## Gate Rules

- Advisor output cannot approve product intent.
- Auto-approval is forbidden.
- Low confidence must surface to the user.

## Next Route

Route only to the next valid Driftlock skill or to `driftlock-amend-advisor` when product intent, UX lock, or spec meaning would change.
