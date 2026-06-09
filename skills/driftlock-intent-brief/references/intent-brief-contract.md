# Driftlock Intent Brief Contract

## Purpose

Create a stable human-readable brief that preserves user intent.

## Required Input

Use the upstream Driftlock artifacts and evidence required by this workflow step. If the required upstream artifact is missing, stop and route backward rather than guessing.

## Required Output

Produce `intent-brief.md` with enough evidence for the next Driftlock skill to continue without re-interrogating product intent.

## Gate Rules

- Do not invent user intent.
- Keep implementation freedom separate from product requirements.
- Do not proceed if user-owned decisions remain unresolved.

## Next Route

Route only to the next valid Driftlock skill or to `driftlock-amend-advisor` when product intent, UX lock, or spec meaning would change.
