# Driftlock Grill Contract

## Purpose

Resolve decision branches until the harness and user share product understanding.

## Required Input

Use the upstream Driftlock artifacts and evidence required by this workflow step. If the required upstream artifact is missing, stop and route backward rather than guessing.

## Required Output

Produce `grill-decisions.jsonl` with enough evidence for the next Driftlock skill to continue without re-interrogating product intent.

## Gate Rules

- If a question can be answered from repo evidence, inspect evidence instead.
- Do not bundle many questions at once.
- Do not ask about code internals unless product intent depends on it.

## Next Route

Route only to the next valid Driftlock skill or to `driftlock-amend-advisor` when product intent, UX lock, or spec meaning would change.
