---
name: driftlock-builder
description: Run build, lint, tests, and runtime checks. Use after implementer or fixer changes code and before review to gather build, lint, test, and runtime evidence.
---

# Driftlock Builder

Verify the implementation mechanically before review.

## Workflow

1. Run the repo-appropriate build, lint, tests, and smoke checks.
2. Record commands, outputs, failures, and confidence.
3. Route pass to reviewer.
4. Route failure to fixer or compound by threshold.

## Rules

- Builder may diagnose but does not silently rewrite implementation.
- Build pass is required before normal review.
- Evidence must be concrete.

## Output

Produce `build-evidence.json`. Read `references/builder-contract.md` for the exact contract.
