---
name: lodestar-mission-control
description: Orchestrate a full Lodestar delegation run from a single request. Use when a user wants to delegate building a complete, ship-grade system or service to AI agents, or says "use Lodestar", "build me ...", or asks to take a vague product idea all the way to a verified, handed-off result through a gated spec-first workflow.
---

# Lodestar Mission Control

The single front door for a Lodestar run. Take one product request and drive
the entire gated pipeline, keeping the user's surface tiny: ask only for
product-level decisions, never mechanical implementation choices.

## Workflow

Invoke the `lodestar-*` skills in order. Never skip a gate.

1. Discovery: `lodestar-survey` -> `lodestar-scout` -> `lodestar-shakedown` -> `lodestar-manifest`.
2. Decision/UX: `lodestar-triage` -> `lodestar-call` -> `lodestar-palette` -> `lodestar-shape` -> `lodestar-shape-lock` -> `lodestar-guard`. Stop for explicit product-shape approval.
3. Lock/Plan: `lodestar-lock` -> `lodestar-checklist` -> `lodestar-stages`.
4. Execution: `lodestar-engineer` -> `lodestar-integrator` -> `lodestar-flight-control` -> `lodestar-eva`, parallel over worktrees.
5. Escalation/Delivery: `lodestar-course-correct` -> `lodestar-debrief` -> `lodestar-dock`.

## Rules

- No implementation before the user approves product shape.
- No locked spec before ambiguity and coverage checks pass.
- A review role never edits code; route fixes to `lodestar-eva`.
- Advisor recommendations are never user approval. Product intent, UX changes,
  and amendments stay user-owned.
- Surface only decision cards, UX preview, amendment approval, and final proof.

## Output

Routes into the pipeline. Read `references/orchestrator-contract.md` for the
exact gate sequence and what to surface to the user.
