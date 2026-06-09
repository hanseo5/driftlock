# Driftlock Implementer Contract

## Purpose

Own code changes for planned work.

## Upstream Contracts

- Superpowers: `third_party/upstream/superpowers/skills/subagent-driven-development`
- Superpowers: `third_party/upstream/superpowers/skills/test-driven-development`
- Superpowers: `third_party/upstream/superpowers/skills/systematic-debugging`
- Superpowers: `third_party/upstream/superpowers/skills/using-git-worktrees`

Implementer owns code mutation. It should work from a single assigned task,
locked spec context, and worktree plan. It reports status using Driftlock's
status vocabulary so the runner can route without guessing.

## Required Input

- `locked-spec.json`
- `task-graph.json`
- assigned task id
- worktree or branch plan
- latest reviewer/fixer notes, when returning from a loop

## Required Output

Produce `implementation-handoff.json` with enough evidence for the next Driftlock skill to continue without re-interrogating product intent.

The handoff must include:

- `status`: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`
- files changed
- commands run
- tests added or updated
- remaining concerns
- exact next recommended route

The runner event sequence is:

- `implementation-started` when implementer begins an assigned task.
- `implementation-ready` when implementation handoff is ready for builder.
- `implementation-blocked` only when the task cannot continue without new context.

## Gate Rules

- Do not change product intent.
- Do not skip builder.
- Do not solve review findings outside assigned scope.
- Do not proceed on a failing baseline without marking the issue as
  pre-existing or routing to fixer/debug.
- Do not ask the user about mechanical implementation choices unless they
  change product behavior, UX, safety, or cost materially.

## Next Route

Route only to the next valid Driftlock skill or to `driftlock-amend-advisor` when product intent, UX lock, or spec meaning would change.
