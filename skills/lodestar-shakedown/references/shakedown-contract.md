# Lodestar Shakedown Contract

## Purpose

Resolve decision branches until the harness and user share product understanding.

## Required Input

Use the upstream Lodestar artifacts and evidence required by this workflow step. If the required upstream artifact is missing, stop and route backward rather than guessing.

## Required Output

Produce `shakedown-decisions.jsonl` with enough evidence for the next Lodestar skill to continue without re-interrogating product intent.

## Gate Rules

- If a question can be answered from repo evidence, inspect evidence instead.
- Do not bundle many questions at once.
- Do not ask about code internals unless product intent depends on it.

## Next Route

Route only to the next valid Lodestar skill or to `lodestar-course-correct` when product intent, UX lock, or spec meaning would change.
