---
name: lodestar-shakedown
description: Stress-test product intent one question at a time. Use when decisions must be resolved before product lock, when the user asks to be stress-tested, or when scout leaves product branches unresolved.
---

# Lodestar Shakedown

Resolve decision branches until the harness and user share product understanding.

## Workflow

1. Ask one question at a time.
2. Provide the recommended answer with each question.
3. Stop asking when product-impacting branches are resolved.
4. Record decisions for lodestar-manifest.

## Rules

- If a question can be answered from repo evidence, inspect evidence instead.
- Do not bundle many questions at once.
- Do not ask about code internals unless product intent depends on it.

## Output

Produce `shakedown-decisions.jsonl`. Read `references/shakedown-contract.md` for the exact contract.
