# Compound Engineering Contract

## Activation Thresholds

- Build/test failures reach the configured debug threshold.
- Review rejects repeat on the same task.
- Review notes identify architecture, coupling, data model, API contract, or UX flow problems.
- Similar defects appear in multiple branches.
- Spec conflict appears during implementation.

## CE Output

A CE pass must produce:

- Failure summary
- Root cause hypothesis
- Evidence list
- Fix brief for implementer/fixer
- Prevention note for future tasks
- Escalation decision: execution, amendment, blocked, or user decision

## Return Path

CE returns to implementer/fixer. The path is:

`CE -> Fix Brief -> Implementer/Fixer -> Build/Test -> Review -> Gate`

CE does not skip build/test or review.

## Learning Notes

Use `templates/learning-note.md`. Keep notes concrete:

- What failed
- Why it failed
- What changed
- What gate or checklist should catch it next time
