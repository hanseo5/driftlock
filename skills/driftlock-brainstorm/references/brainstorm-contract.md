# Driftlock Brainstorm Contract

## Purpose

Expose meaningful alternatives without drifting into implementation.

## Required Input

Use the upstream Driftlock artifacts and evidence required by this workflow step. If the required upstream artifact is missing, stop and route backward rather than guessing.

## Required Output

Produce `brainstorm-notes.md` with enough evidence for the next Driftlock skill to continue without re-interrogating product intent.

## Gate Rules

- Keep brainstorming bounded.
- Do not treat suggestions as approvals.
- Do not create a Locked Spec.

## Next Route

Route only to the next valid Driftlock skill or to `driftlock-amend-advisor` when product intent, UX lock, or spec meaning would change.
