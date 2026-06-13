# Lodestar Upstream Map

Lodestar is now a completeness-first harness. That means upstream projects are
not merely inspiration; selected files are vendored and mapped into Lodestar's
own contracts.

## Import Rule

Vendored upstream skills and templates are reference material. The Lodestar
plugin exposes only `lodestar-*` skills, and those skills must route through
Lodestar gates, runner states, and artifact validators.

## Layers

| Layer | Primary upstream | Lodestar responsibility |
| --- | --- | --- |
| Office Hours UI | gstack, Superpowers | Turn raw requests into decision cards and approved product shape. |
| Spec Engine | Spec Kit | Clarify, analyze, specify, plan, and task-split with locked evidence. |
| Execution Engine | Superpowers | Worktree isolation, fresh implementer loops, TDD, debug, verification. |
| Quality Engine | Compound Engineering, gstack | Multi-persona review, browser/design QA, proof evidence. |
| Compound Memory | Compound Engineering, gstack | Repeated failure learning, solution notes, context save/restore. |
| Delivery Engine | gstack, Superpowers | Ship checklist, final branch handoff, proof bundle. |

## Adapter Requirement

Every upstream behavior must pass through a Lodestar adapter. The adapter
translates foreign skill assumptions into Lodestar primitives:

- input artifact
- output artifact
- allowed mutation scope
- gate criteria
- runner transition
- failure route
- evidence path

## User Intent Ownership

Models and advisor tools can recommend. They cannot approve product intent,
UX changes, destructive actions, or amendments that alter the locked spec. Those
remain user-owned decisions.
