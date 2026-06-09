---
name: driftlock-decision-classify
description: Classify decisions by owner and approval policy. Use when product, UX, safety, scope, or implementation decisions need routing into mechanical, taste, user-challenge, or safety-destructive classes.
---

# Driftlock Decision Classify

Prevent the user from being asked to decide details that the harness can safely handle.

## Workflow

1. Classify each decision as mechanical, taste, user-challenge, or safety-destructive.
2. Assign owner: harness, user, or advisor.
3. Choose default action for each class.
4. Output decision-policy evidence for product lock.

## Rules

- Mechanical choices may be auto-resolved with evidence.
- Taste and user-challenge choices require user approval.
- Safety/destructive choices require explicit approval.

## Output

Produce `decision-policy.json`. Read `references/decision-classify-contract.md` for the exact contract.
