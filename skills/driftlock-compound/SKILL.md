---
name: driftlock-compound
description: Activate Driftlock compound engineering for repeated failures, repeated review rejects, structural design problems, recurring mistakes, or high-risk long-horizon work. Use to create CE briefs, learning notes, and escalation decisions before routing work back to implementer/fixer agents.
---

# Driftlock Compound

Use this skill when normal debug or review loops are no longer enough.

## Activation

Activate CE conditionally when any of these are true:

- The same task hits repeated build/test failures.
- Review rejects reveal a structural design problem.
- The same mistake recurs across tasks.
- A spec gap or architecture mismatch is discovered.
- The work is high-risk and long-horizon enough to need stronger memory.

## Workflow

1. Gather failure evidence, review notes, diffs, test output, and prior attempts.
2. Identify root cause and whether the issue is implementation, task split, architecture, or spec.
3. Write a CE Fix Brief for the implementer/fixer.
4. Add a learning note that prevents the same failure from recurring.
5. Return to the implementer/fixer, not directly to review.
6. Escalate to `driftlock-amend` only for product-impacting spec changes.

## Rules

- CE is not always on.
- CE does not own final product intent.
- CE produces instructions and learning; implementation agents still make code changes.
- After CE, the task goes back through implementer -> build/test -> review.

## Output

Produce a handoff object in `phase: ce` and a learning note using `templates/learning-note.md`.

For the exact CE contract, read `references/compound-contract.md`.
