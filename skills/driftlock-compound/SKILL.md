---
name: driftlock-compound
description: Escalate repeated failures into CE learning. Use when repeated build failures, repeated review rejects, structural design problems, recurring mistakes, or high-risk long-horizon work require compound engineering.
---

# Driftlock Compound

Create root-cause learning and a fix brief without skipping execution gates.

## Workflow

1. Gather failure evidence and prior attempts.
2. Identify root cause and prevention rule.
3. Write ce-synthesis.json and ce-brief.md.
4. Route to fixer or amend advisor, never directly to review or handoff.

## Rules

- CE is conditional, not always on.
- CE does not edit code directly.
- CE must return through fixer/implementer and builder.

## Output

Produce `ce-synthesis.json` and `ce-brief.md`. Read `references/compound-contract.md` for the exact contract.
