# Lodestar Orchestrator Contract

## Purpose

Run a complete Lodestar delegation from one request, holding every gate, while
keeping the user-facing surface small enough for a non-developer.

## Run Modes

Ask the user once, at the start, how hands-on they want to be:

- **Guided** (default): surface every genuine product decision as a decision
  card and wait for the user.
- **Express / Autopilot**: take the recommended option on ordinary product
  decisions and only stop for safety, cost, hard-to-reverse choices, wireframe
  approval, design-system approval, final UI/UX approval, and amendments.

In both modes, wireframe approval, design-system approval, and final UI/UX
approval are required before any implementation starts.

## How To Ask The User

- Every user-facing question carries a recommended answer and a safe default in
  plain product language.
- The user can always reply "use your recommendations" to accept all pending
  recommendations at once.
- Ask user-challenge and safety-destructive decisions one at a time.

## Preview Flow

1. `lodestar-shape` produces `wireframe.html`.
2. Open `wireframe.html` in a local browser when available. Do not hand the user
   a file path and wait for them to open it.
3. Stop for explicit structure and flow approval.
4. `lodestar-palette` presents design-system choices: tone, density, component
   style, typography, color direction, motion/interaction rules, platform
   feel, product archetype, benchmark bar, and release-quality acceptance
   criteria.
5. Stop for explicit design-system approval.
6. `lodestar-shape` produces `shape.html` using the approved design direction.
7. `lodestar-shape` runs the release-quality visual QA loop and writes
   `visual-qa.md`.
8. Open `shape.html` in a local browser when available.
9. Stop for explicit final UI/UX approval only after visual QA passes.

## Gate Sequence

| Phase | Skills | Non-negotiable gate |
| --- | --- | --- |
| BRIEFING | survey, scout, shakedown, manifest | Ambiguity that changes product shape is resolved with the user before planning. |
| ALIGNMENT | triage, call, shape wireframe, palette, shape final, shape-lock, guard | No implementation before wireframe, design-system, and final UI/UX approval. |
| CLEARANCE | lock, checklist, stages | No locked spec before ambiguity and coverage checks pass. |
| ASCENT | engineer, integrator, flight-control, eva | A review role may never edit code. Fixes route to eva. |
| DOCKING | course-correct, debrief, dock | Final handoff requires build, review, guard, amendment, integration, QA, and proof evidence. |

## Surface To The User

- decision cards for genuine product trade-offs
- wireframe preview approval
- design-system approval
- final UI/UX preview approval
- amendment approval when a change alters the locked product
- final handoff with proof

## Handle Silently

- subagent routing, review persona selection, worktree mechanics
- schema, validator, and runner-state internals
- mechanical implementation choices that do not change product behavior, UX,
  safety, or cost

## User Intent Ownership

Models and advisor tools recommend; they never approve product intent, UX
changes, destructive actions, or amendments to the locked spec. Those remain
user-owned.

## Next Route

Begin by setting the run mode, then `lodestar-survey`. If a request would change
product intent, UX lock, or spec meaning mid-run, route to
`lodestar-course-correct`.
