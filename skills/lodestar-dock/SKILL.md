---
name: lodestar-dock
description: Deliver only after all gates pass. Use when all tasks, UX guard, build evidence, review reports, amendments, and integration checks are complete and the final result can be handed to the user.
---

# Lodestar Dock

Produce final delivery evidence without hiding remaining risk.

## Workflow

1. Verify task, build, review, UX guard, amendment, and integration statuses.
2. Summarize what changed and how it was verified.
3. List residual risks and follow-ups.
4. Output final-handoff.json.

## Rules

- Do not hand off with failing or missing gates.
- Do not treat advisor recommendation as user approval.
- Do not omit evidence.

## Output

Produce `final-handoff.json`. Read `references/dock-contract.md` for the exact contract.
