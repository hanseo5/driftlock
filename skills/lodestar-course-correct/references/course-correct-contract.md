# Lodestar Course Correct Contract

## Purpose

Translate spec conflicts into user-decidable product options.

## Required Input

Use the upstream Lodestar artifacts and evidence required by this workflow step. If the required upstream artifact is missing, stop and route backward rather than guessing.

## Required Output

Produce `amendment-request.json` with enough evidence for the next Lodestar skill to continue without re-interrogating product intent.

## Gate Rules

- Advisor output cannot approve product intent.
- Auto-approval is forbidden.
- Low confidence must surface to the user.

## Next Route

Route only to the next valid Lodestar skill or to `lodestar-course-correct` when product intent, UX lock, or spec meaning would change.
