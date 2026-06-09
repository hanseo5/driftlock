---
name: driftlock-task-split
description: Split the locked spec into branch-sized tasks. Use after spec gate passes to create task graph, dependencies, branch names, and acceptance coverage for execution agents.
---

# Driftlock Task Split

Turn the Locked Spec into safe units of agent work.

## Workflow

1. Create tasks with branch names, dependencies, acceptance criteria, and coverage IDs.
2. Ensure every success criterion and scenario is covered.
3. Keep tasks branch-sized.
4. Output task-graph.json.

## Rules

- Do not start implementation before task split passes.
- Do not leave uncovered acceptance criteria.
- Do not create dependency cycles.

## Output

Produce `task-graph.json`. Read `references/task-split-contract.md` for the exact contract.
