# Driftlock UX Approval Contract

## Purpose

Make UX approval an explicit gate before product lock.

## Required Input

Use the upstream Driftlock artifacts and evidence required by this workflow step. If the required upstream artifact is missing, stop and route backward rather than guessing.

## Required Output

Produce `ux-lock.md` with enough evidence for the next Driftlock skill to continue without re-interrogating product intent.

## Gate Rules

- User approval is required.
- Advisors cannot approve product shape.
- Approved preview must be referenced by product lock.

## Next Route

Route only to the next valid Driftlock skill or to `driftlock-amend-advisor` when product intent, UX lock, or spec meaning would change.
