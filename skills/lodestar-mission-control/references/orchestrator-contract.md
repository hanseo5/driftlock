# Lodestar Orchestrator Contract

## Purpose

Run a complete Lodestar delegation from one request, holding every gate, while
keeping the user-facing surface small.

## Gate Sequence

| Phase | Skills | Non-negotiable gate |
| --- | --- | --- |
| Discovery | survey, scout, shakedown, intent-brief | Ambiguity that changes product shape is resolved with the user before planning. |
| Decision/UX | decision-classify, decision-card, design-system-lite, ux-preview, ux-approval, ux-guard | No implementation before product-shape approval. |
| Lock/Plan | product-lock, spec-gate, task-split | No locked spec before Spec Kit-style ambiguity and coverage checks pass. |
| Execution | implementer, builder, reviewer, fixer | A review role may never edit code. Fixes route to fixer. |
| Escalation/Delivery | amend-advisor, debrief, handoff | Debrief cannot jump to review or handoff; it returns through fixer or implementer/builder. Final handoff requires build, review, UX guard, amendment, integration, QA, and proof evidence. |

## Surface to the user

- decision cards (genuine product trade-offs)
- UX preview, for approval
- amendment approval when a change alters the locked spec
- final handoff with proof

## Handle silently

- subagent routing, review persona selection, worktree mechanics
- schema, validator, and runner-state internals
- mechanical implementation choices that do not change product behavior, UX,
  safety, or cost

## User Intent Ownership

Models and advisor tools recommend; they never approve product intent, UX
changes, destructive actions, or amendments to the locked spec. Those remain
user-owned.

## Next Route

Begin at `lodestar-survey`. If a request would change product intent, UX
lock, or spec meaning mid-run, route to `lodestar-course-correct`.
