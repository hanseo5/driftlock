# Driftlock Completeness-First Architecture

## Objective

Build Driftlock as a reference-grade AI development delegation harness. Internal
complexity is allowed when it improves correctness, recovery, proof, and final
product quality. External user-facing complexity must remain low.

## Architecture Shift

The first Driftlock rebuild created 20 first-class skills and a small runner.
The completeness-first version adds a deeper engine underneath those skills:

1. Upstream registry and attribution
2. Office-hours product judgment
3. Spec Kit based spec engine
4. Superpowers based execution loop
5. Compound Engineering based quality and learning engine
6. gstack based QA, design review, ship, and context persistence
7. Proof bundle driven final handoff

## Runner Responsibility

The runner is no longer only a phase transition checker. It owns the run record:

- `.driftlock/runs/<run-id>/`
- upstream source snapshot metadata
- product decisions and UX approvals
- locked spec and spec gate evidence
- task graph and worktree plan
- implementation/build/review/fix state
- CE cycles and learning notes
- amendment advisor state
- QA/design/browser evidence
- final proof bundle

## External Simplicity

The user should see:

- decision cards
- UX preview approval
- amendment approval when product intent changes
- final handoff with proof

The user should not need to understand:

- subagent routing
- review persona selection
- worktree details
- CE schema details
- runner state internals

## Non-Negotiable Gates

- No implementation before product shape approval.
- No locked spec before Spec Kit style ambiguity and coverage checks pass.
- No review role may edit code.
- CE cannot jump directly to review or handoff; it must return through fixer or implementer and builder.
- Advisor tools cannot auto-approve product intent.
- Final handoff requires build, review, UX guard, amendment, integration, QA, and proof evidence.
