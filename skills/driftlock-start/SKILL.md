---
name: driftlock-start
description: Orchestrate a full Driftlock delegation run from a single request. Use when a user wants to delegate building a complete, ship-grade system or service to AI agents, or says "use Driftlock", "build me ...", or asks to take a vague product idea all the way to a verified, handed-off result through a gated spec-first workflow.
---

# Driftlock Start

The single front door for a Driftlock run. Take one product request and drive
the entire gated pipeline, keeping the user's surface tiny: ask only for
product-level decisions, never mechanical implementation choices.

## Workflow

Invoke the `driftlock-*` skills in order. Never skip a gate.

1. Discovery: `driftlock-office-hours` -> `driftlock-brainstorm` -> `driftlock-grill` -> `driftlock-intent-brief`.
2. Decision/UX: `driftlock-decision-classify` -> `driftlock-decision-card` -> `driftlock-design-system-lite` -> `driftlock-ux-preview` -> `driftlock-ux-approval` -> `driftlock-ux-guard`. Stop for explicit product-shape approval.
3. Lock/Plan: `driftlock-product-lock` -> `driftlock-spec-gate` -> `driftlock-task-split`.
4. Execution: `driftlock-implementer` -> `driftlock-builder` -> `driftlock-reviewer` -> `driftlock-fixer`, parallel over worktrees.
5. Escalation/Delivery: `driftlock-amend-advisor` -> `driftlock-compound` -> `driftlock-handoff`.

## Rules

- No implementation before the user approves product shape.
- No locked spec before ambiguity and coverage checks pass.
- A review role never edits code; route fixes to `driftlock-fixer`.
- Advisor recommendations are never user approval. Product intent, UX changes,
  and amendments stay user-owned.
- Surface only decision cards, UX preview, amendment approval, and final proof.

## Output

Routes into the pipeline. Read `references/orchestrator-contract.md` for the
exact gate sequence and what to surface to the user.
