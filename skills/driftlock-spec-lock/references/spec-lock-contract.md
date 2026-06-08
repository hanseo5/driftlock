# Spec Lock Contract

## Required Sequence

1. Intent capture
2. Brainstorming
3. Grill-me interrogation
4. Spec draft
5. Clarify gate
6. Checklist gate
7. Analyze gate
8. Locked Spec

## Gate Criteria

- Intent gate passes when the primary user, outcome, constraints, risks, and non-goals are explicit.
- Grill gate passes when each important decision branch has a recorded question and answer.
- Spec gate passes when success criteria and acceptance scenarios are testable.
- Analyze gate passes when edge cases, dependencies, failure modes, and handoff assumptions are documented.

## Locked Spec Minimum

- `status` is `locked`.
- Every success criterion has `testable: true`.
- Every acceptance scenario has given, when, and then.
- Every product-impacting decision records its source.
- `gate_evidence.intent_gate`, `grill_gate`, `spec_gate`, and `analyze_gate` are all `pass`.

## Failure Handling

- Missing user intent: continue grill-me.
- Technical feasibility uncertainty: ask an advisor, then return to the user with options.
- Spec conflict after lock: route to `driftlock-amend`.
- Implementation detail uncertainty that does not affect product intent: leave freedom to execution agents.
