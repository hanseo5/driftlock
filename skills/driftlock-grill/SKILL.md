---
name: driftlock-grill
description: Stress-test product intent one question at a time. Use when decisions must be resolved before product lock, when the user asks to be grilled, or when brainstorm leaves product branches unresolved.
---

# Driftlock Grill

Resolve decision branches until the harness and user share product understanding.

## Workflow

1. Ask one question at a time.
2. Provide the recommended answer with each question.
3. Stop asking when product-impacting branches are resolved.
4. Record decisions for driftlock-intent-brief.

## Rules

- If a question can be answered from repo evidence, inspect evidence instead.
- Do not bundle many questions at once.
- Do not ask about code internals unless product intent depends on it.

## Output

Produce `grill-decisions.jsonl`. Read `references/grill-contract.md` for the exact contract.
