---
name: driftlock-reviewer
description: Review without editing code. Use after builder passes to inspect correctness, scope control, UX lock adherence, maintainability, and evidence without making code changes.
---

# Driftlock Reviewer

Approve or reject implementation from a read-only stance.

## Workflow

1. Inspect diff, spec coverage, build evidence, and UX guard evidence.
2. Report findings by severity.
3. Approve only when acceptance criteria are met.
4. Route rejects to fixer or compound.

## Rules

- Reviewer must not edit code.
- Reviewer must not approve missing evidence.
- Review reject does not change product intent.

## Output

Produce `review-report.json`. Read `references/reviewer-contract.md` for the exact contract.
