---
name: lodestar-debrief
description: Escalate repeated failures into Debrief learning. Use when repeated build failures, repeated review rejects, structural design problems, recurring mistakes, or high-risk long-horizon work require debrief.
---

# Lodestar Debrief

Create root-cause learning and a fix brief without skipping execution gates.

## Workflow

1. Gather failure evidence and prior attempts.
2. Identify root cause and prevention rule.
3. Write debrief.json and debrief-brief.md.
4. Route to fixer or amend advisor, never directly to review or handoff.

## Rules

- Debrief is conditional, not always on.
- Debrief does not edit code directly.
- Debrief must return through fixer/implementer and builder.

## Output

Produce `debrief.json` and `debrief-brief.md`. Read `references/debrief-contract.md` for the exact contract.
