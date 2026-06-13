# Lodestar Orchestrator Contract

## Purpose

Run a complete Lodestar delegation from one request, holding every gate, while
keeping the user-facing surface small enough for a non-developer.

## Run modes

Ask the user once, at the start, how hands-on they want to be:

- **Guided** (default) — surface every genuine product decision as a decision
  card and wait for the user.
- **Express / Autopilot** — take the recommended option on every product
  decision automatically, and only stop the user for: a `safety-destructive`
  action, anything that costs money or is hard to reverse, and the one
  product-shape approval. Log every auto-taken choice so the user can review it.

In both modes the product-shape preview is still shown and approved before any
code is written.

## How to ask the user

- Every user-facing question carries a **recommended answer** and a **safe
  default**, in plain product language — never implementation jargon.
- The user can always reply "use your recommendations" to accept all pending
  recommendations at once.
- Ask `user-challenge` and `safety-destructive` decisions one at a time; never
  bundle them.

## Show the preview

`lodestar-shape` produces `shape.html`. Do not hand the user a file path —
render it: open it in a browser or capture a screenshot and present it inline,
then ask for approval. A non-developer should never have to open a file
themselves.

## Gate Sequence

| Phase | Skills | Non-negotiable gate |
| --- | --- | --- |
| BRIEFING | survey, scout, shakedown, manifest | Ambiguity that changes product shape is resolved with the user before planning. |
| ALIGNMENT | triage, call, palette, shape, shape-lock, guard | No implementation before product-shape approval. |
| CLEARANCE | lock, checklist, stages | No locked spec before Spec Kit-style ambiguity and coverage checks pass. |
| ASCENT | engineer, integrator, flight-control, eva | A review role (flight-control) may never edit code. Fixes route to eva. |
| DOCKING | course-correct, debrief, dock | Debrief cannot jump to review or handoff; it returns through eva or engineer/integrator. Final handoff requires build, review, guard, amendment, integration, QA, and proof evidence. |

## Surface to the user

- decision cards (genuine product trade-offs)
- the product-shape preview, for approval
- amendment approval when a change alters the locked spec
- the final handoff with proof

## Handle silently

- subagent routing, review persona selection, worktree mechanics
- schema, validator, and runner-state internals
- mechanical implementation choices that do not change product behavior, UX,
  safety, or cost

## User Intent Ownership

Models and advisor tools recommend; they never approve product intent, UX
changes, destructive actions, or amendments to the locked spec. Those remain
user-owned, even in express mode for the `user-challenge` and
`safety-destructive` classes.

## Next Route

Begin by setting the run mode, then `lodestar-survey`. If a request would change
product intent, UX lock, or spec meaning mid-run, route to
`lodestar-course-correct`.
