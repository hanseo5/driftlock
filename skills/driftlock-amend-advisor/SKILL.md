---
name: driftlock-amend-advisor
description: Advise on product-impacting spec amendments. Use when implementation reveals ambiguity, contradiction, infeasibility, UX change, scope change, or advisor fallback is needed before user approval.
---

# Driftlock Amend Advisor

Translate spec conflicts into user-decidable product options.

## Workflow

1. Freeze affected execution path.
2. Classify issue as implementation bug or product-impacting amendment.
3. Ask Claude first when available, Codex second-pass as fallback.
4. Create amendment-request.json requiring user approval.

## Rules

- Advisor output cannot approve product intent.
- Auto-approval is forbidden.
- Low confidence must surface to the user.

## Output

Produce `amendment-request.json`. Read `references/amend-advisor-contract.md` for the exact contract.
