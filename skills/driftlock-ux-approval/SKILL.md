---
name: driftlock-ux-approval
description: Capture approval of the shown product shape. Use after a UX preview is shown and the user must approve, reject, or amend product shape before Locked Spec creation.
---

# Driftlock UX Approval

Make UX approval an explicit gate before product lock.

## Workflow

1. Ask whether the preview matches the intended product shape.
2. Record approved first screen, flow, density, and must-not-drift rules.
3. Write ux-lock.md when approved.
4. Return to preview when rejected.

## Rules

- User approval is required.
- Advisors cannot approve product shape.
- Approved preview must be referenced by product lock.

## Output

Produce `ux-lock.md`. Read `references/ux-approval-contract.md` for the exact contract.
