# Driftlock Decision Classify Contract

## Purpose

Prevent the user from being asked to decide details that the harness can safely handle.

## Required Input

Use the upstream Driftlock artifacts and evidence required by this workflow step. If the required upstream artifact is missing, stop and route backward rather than guessing.

## Required Output

Produce `decision-policy.json` with enough evidence for the next Driftlock skill to continue without re-interrogating product intent.

## Gate Rules

- Mechanical choices may be auto-resolved with evidence.
- Taste and user-challenge choices require user approval.
- Safety/destructive choices require explicit approval.

## Next Route

Route only to the next valid Driftlock skill or to `driftlock-amend-advisor` when product intent, UX lock, or spec meaning would change.
