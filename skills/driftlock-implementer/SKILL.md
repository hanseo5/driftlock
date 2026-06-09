---
name: driftlock-implementer
description: Make code changes for an assigned task. Use when a validated task from task-graph.json should be implemented on its branch or worktree according to Locked Spec and UX lock constraints.
---

# Driftlock Implementer

Own code changes for planned work.

## Workflow

1. Read task acceptance criteria and dependencies.
2. Change only files needed for the task.
3. Preserve UX lock and product intent.
4. Hand off to builder with evidence.

## Rules

- Do not change product intent.
- Do not skip builder.
- Do not solve review findings outside assigned scope.

## Output

Produce `implementation-handoff.json`. Read `references/implementer-contract.md` for the exact contract.
