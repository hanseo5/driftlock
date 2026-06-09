---
name: driftlock-decision-card
description: Present product-impacting choices clearly. Use when a user-owned product, UX, amendment, safety, or scope decision must be presented as a recommendation with choices and consequences.
---

# Driftlock Decision Card

Translate internal complexity into a decision the user can make confidently.

## Workflow

1. State the decision in product language.
2. Show recommended answer first.
3. Show consequence, risk, and default if no answer is provided.
4. Record the selected option in decision-card.json.

## Rules

- Do not expose raw implementation trivia.
- Do not hide product tradeoffs.
- Do not auto-approve user-owned decisions.

## Output

Produce `decision-card.json`. Read `references/decision-card-contract.md` for the exact contract.
