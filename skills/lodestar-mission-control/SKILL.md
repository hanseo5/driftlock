---
name: lodestar-mission-control
description: Orchestrate a full Lodestar run from a single request, keeping users focused on product decisions while agents handle the mechanics.
---

# Lodestar Mission Control

The single front door for a Lodestar run. Take one product request and drive the
entire pipeline while keeping the user's surface small: ask only for
product-level decisions, never mechanical implementation choices.

## Workflow

First, set the run mode: ask whether the user wants **guided** (check each
product decision) or **express** (take recommendations automatically, stop only
for cost, irreversible, safety, wireframe approval, design-system approval, and
final UI/UX approval). Then invoke the `lodestar-*` skills in order. Never skip
a gate.

1. Discovery: `lodestar-survey` -> `lodestar-scout` -> `lodestar-shakedown` ->
   `lodestar-manifest`.
2. Decision/UX: `lodestar-triage` -> `lodestar-call` -> `lodestar-shape`
   wireframe -> `lodestar-palette` -> `lodestar-shape` final UI/UX ->
   `lodestar-shape-lock` -> `lodestar-guard`.
   Open `wireframe.html` locally and stop for structure approval. Present
   design-system choices and stop for visual direction approval. Open
   `shape.html` locally and stop for final UI/UX approval.
3. Lock/Plan: `lodestar-lock` -> `lodestar-checklist` -> `lodestar-stages`.
4. Execution: `lodestar-engineer` -> `lodestar-integrator` ->
   `lodestar-flight-control` -> `lodestar-eva`.
5. Escalation/Delivery: `lodestar-course-correct` -> `lodestar-debrief` ->
   `lodestar-dock`.

## Rules

- No implementation before the user approves the wireframe, design system, and
  final UI/UX preview.
- No locked spec before ambiguity and coverage checks pass.
- A review role never edits code; route fixes to `lodestar-eva`.
- Advisor recommendations are never user approval. Product intent, UX changes,
  and amendments stay user-owned.
- Every user-facing question carries a recommended answer and a safe default in
  plain language; the user can reply "use your recommendations" to accept all.
- Surface only decision cards, wireframe approval, design-system approval, final
  UI/UX approval, amendment approval, and final proof.

## Output

Routes into the pipeline. Read `references/orchestrator-contract.md` for the
exact gate sequence and what to surface to the user.
