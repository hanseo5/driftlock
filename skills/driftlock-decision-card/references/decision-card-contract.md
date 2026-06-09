# Driftlock Decision Card Contract

## Purpose

Translate internal complexity into a decision the user can make confidently.

## Required Input

Use the upstream Driftlock artifacts and evidence required by this workflow step. If the required upstream artifact is missing, stop and route backward rather than guessing.

## Required Output

Produce `decision-card.json` with enough evidence for the next Driftlock skill to continue without re-interrogating product intent.

## Gate Rules

- Do not expose raw implementation trivia.
- Do not hide product tradeoffs.
- Do not auto-approve user-owned decisions.

## Next Route

Route only to the next valid Driftlock skill or to `driftlock-amend-advisor` when product intent, UX lock, or spec meaning would change.
