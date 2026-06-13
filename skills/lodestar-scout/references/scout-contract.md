# Lodestar Scout Contract

## Purpose

Expose meaningful alternatives without drifting into implementation.

## Required Input

Use the upstream Lodestar artifacts and evidence required by this workflow step. If the required upstream artifact is missing, stop and route backward rather than guessing.

## Required Output

Produce `scout-notes.md` with enough evidence for the next Lodestar skill to continue without re-interrogating product intent.

## Gate Rules

- Keep scouting bounded.
- Do not treat suggestions as approvals.
- Do not create a Locked Spec.

## Next Route

Route only to the next valid Lodestar skill or to `lodestar-course-correct` when product intent, UX lock, or spec meaning would change.
