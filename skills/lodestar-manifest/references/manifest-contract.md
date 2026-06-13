# Lodestar Manifest Contract

## Purpose

Create a stable human-readable brief that preserves user intent.

## Required Input

Use the upstream Lodestar artifacts and evidence required by this workflow step. If the required upstream artifact is missing, stop and route backward rather than guessing.

## Required Output

Produce `manifest.md` with enough evidence for the next Lodestar skill to continue without re-interrogating product intent.

## Gate Rules

- Do not invent user intent.
- Keep implementation freedom separate from product requirements.
- Do not proceed if user-owned decisions remain unresolved.

## Next Route

Route only to the next valid Lodestar skill or to `lodestar-course-correct` when product intent, UX lock, or spec meaning would change.
