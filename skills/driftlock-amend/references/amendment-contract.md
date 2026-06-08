# Amendment Contract

## Amendment Classes

- Clarification: wording is unclear but intent is stable.
- Contradiction: locked requirements cannot all be true.
- Infeasibility: requirement cannot be implemented under current constraints.
- Scope change: desired behavior is outside the locked spec.
- Implementation bug: no amendment needed; return to execution.

## Advisor Policy

- Prefer Claude CLI for an independent architecture or feasibility pass.
- If Claude is unavailable, rate-limited, or fails, use Codex second-pass review.
- If both are unavailable, create a local evidence-based recommendation and mark confidence low.
- Advisor output never approves product intent. It supplies options, risks, and recommendation.

## User Approval

Ask the user only after the issue is translated into product-level options:

- Keep locked spec and adjust implementation.
- Amend locked spec with a specific change.
- Defer change to non-goal or later phase.
- Stop and redesign.

## Re-Lock

After approval:

- Update decisions with source `amendment`.
- Update success criteria or acceptance scenarios when needed.
- Re-run clarify, checklist, and analyze gates.
- Resume execution from the affected task split.
