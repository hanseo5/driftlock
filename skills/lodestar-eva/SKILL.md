---
name: lodestar-eva
description: Apply fixes after build or review failure. Use when builder, reviewer, UX guard, or debrief produces a concrete fix brief for an existing task.
---

# Lodestar EVA

Own code changes after failure feedback.

## Workflow

1. Read failure evidence and fix brief.
2. Apply the smallest scoped fix.
3. Preserve product and UX locks.
4. Return to builder, not directly to review or handoff.

## Rules

- Do not bypass builder.
- Do not broaden scope silently.
- Route spec or product conflicts to amend advisor.

## Output

Produce `fix-handoff.json`. Read `references/eva-contract.md` for the exact contract.
