---
name: driftlock-execute
description: Run gated long-horizon implementation from a Driftlock Locked Spec. Use when a locked spec should be split into tasks, assigned to implementer/build-review loops, validated through build/test/review gates, merged, and handed off only after all gates pass.
---

# Driftlock Execute

Use this skill after `driftlock-spec-lock` has produced a valid Locked Spec.

## Workflow

1. Validate the Locked Spec before creating tasks.
2. Split work into branch-sized tasks with explicit dependencies and acceptance criteria.
3. Run the Task Split Gate before implementation.
4. For each task, route through implementer -> build/test -> review -> gate.
5. On build or test failure, route to Debug Mode and back to the implementer/fixer.
6. On review reject, route to CE only when escalation criteria are met, then back to the implementer/fixer.
7. Merge only after task gates pass.
8. Run the Integration Gate and produce final handoff only after all tasks and global acceptance criteria pass.

## Rules

- Review agents review and reject or approve. They do not perform code changes.
- Builder/build-test agents execute builds, tests, lint, and runtime checks. They may diagnose but should not silently rewrite implementation.
- Implementer/fixer agents own code changes after debug or CE instructions.
- Long horizon is allowed, but every loop needs state, evidence, and a next action.
- Spec-impacting conflicts route to `driftlock-amend` instead of being solved silently.

## Output

Produce task graphs matching `schemas/tasks.schema.json` and handoff objects matching `schemas/handoff.schema.json`.

For the exact gate contract, read `references/execution-contract.md`.
