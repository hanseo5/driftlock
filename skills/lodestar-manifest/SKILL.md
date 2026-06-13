---
name: lodestar-manifest
description: Compress clarified intent into a handoff artifact. Use after survey, scout, and shakedown have enough decisions to summarize the product goal for downstream UX and spec work.
---

# Lodestar Manifest

Create a stable human-readable brief that preserves user intent.

## Workflow

1. Summarize primary user, outcome, constraints, non-goals, risks, and open questions.
2. Cite decision sources from survey, scout, and shakedown.
3. Mark unresolved product choices as blockers for UX approval.
4. Output manifest.md.

## Rules

- Do not invent user intent.
- Keep implementation freedom separate from product requirements.
- Do not proceed if user-owned decisions remain unresolved.

## Output

Produce `manifest.md`. Read `references/manifest-contract.md` for the exact contract.
