# Lodestar Call Contract

## Purpose

Translate internal complexity into a decision the user can make confidently.

## Required Input

Use the upstream Lodestar artifacts and evidence required by this workflow step. If the required upstream artifact is missing, stop and route backward rather than guessing.

## Required Output

Produce `call.json` with enough evidence for the next Lodestar skill to continue without re-interrogating product intent.

## Gate Rules

- Do not expose raw implementation trivia.
- Do not hide product tradeoffs.
- Do not auto-approve user-owned decisions.

## Next Route

Route only to the next valid Lodestar skill or to `lodestar-course-correct` when product intent, UX lock, or spec meaning would change.
