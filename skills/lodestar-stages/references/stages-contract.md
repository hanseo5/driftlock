# Lodestar Stages Contract

## Purpose

Turn the Locked Spec into safe units of agent work.

## Upstream Contracts

- Spec Kit: `third_party/upstream/spec-kit/templates/commands/tasks.md`
- Spec Kit: `third_party/upstream/spec-kit/templates/tasks-template.md`
- Superpowers: `third_party/upstream/superpowers/skills/writing-plans`
- Superpowers: `third_party/upstream/superpowers/skills/subagent-driven-development`

Task split must create work units that are independently executable, reviewable,
and traceable to locked success criteria or acceptance scenarios.

## Required Input

- `locked-spec.json`
- `checklist-report.json`
- known repo setup and worktree constraints

## Required Output

Produce `task-graph.json` with enough evidence for the next Lodestar skill to continue without re-interrogating product intent.

Each task should include:

- `parallel_group`: the batch group it can run with when dependencies are clear
- `write_scope`: files, modules, or ownership boundaries the task may edit
- `merge_risk`: `low`, `medium`, or `high`

After task split passes, the spec is considered SDD-ready. Start the execution
driver with:

```powershell
lodestar.py execution-start --task-graph task-graph.json --spec locked-spec.json --run-dir .lodestar/runs/<run-id>
```

This creates `execution-plan.json`, `tasks/<task-id>/state.json`,
`dispatch/<task-id>-agent-dispatch.json`, and
`dispatch/agent-dispatch-batch.json`. The dispatch artifacts are the bridge
from locked SDD preparation into Superpowers-style execution: implementer,
builder, reviewer, fixer, debrief, and amendment roles advance through the
gated loop without asking the user to manually choose every next command.

Use `execution-dispatch-batch` to refresh the max-parallel batch. The batch
must include every dependency-unblocked `TASK_READY` task and every task already
inside the execution loop.

Use lower-level `execution-init` only when a caller explicitly wants to create
state files without dispatching the first runnable agent task.

## Gate Rules

- Do not start implementation before task split passes.
- Do not leave uncovered acceptance criteria.
- Do not create dependency cycles.
- Do not hide unnecessary serial bottlenecks when tasks can be split safely.
- Do not omit write scope or merge risk for new task graphs.
- Do not assign product intent decisions to implementers.
- Do not create tasks that cannot be validated by builder/reviewer evidence.

## Next Route

Route only to the next valid Lodestar skill or to `lodestar-course-correct` when product intent, UX lock, or spec meaning would change.
