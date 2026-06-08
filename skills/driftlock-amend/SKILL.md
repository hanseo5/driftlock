---
name: driftlock-amend
description: Resolve spec conflicts and product-impacting amendments in Driftlock. Use when implementation reveals an ambiguous, contradictory, infeasible, or missing requirement; when an agent proposes changing locked product intent; or when Claude/Codex advisors should analyze an amendment before the user approves it.
---

# Driftlock Amend

Use this skill when the Locked Spec may need to change. Models advise; the user owns product intent.

## Workflow

1. Freeze execution for the affected task or dependency chain.
2. Classify the issue as clarification, contradiction, infeasibility, scope change, or implementation bug.
3. If it is only an implementation bug, return to `driftlock-execute`.
4. If it is spec-impacting, produce an Amendment Request with options and consequences.
5. Ask an advisor when useful: Claude first, Codex second-pass fallback if Claude is unavailable or rate-limited.
6. Translate advisor output into product-level tradeoffs the user can decide.
7. Resume only after user approval and spec re-lock.

## Rules

- Do not auto-approve product-impacting amendments.
- Low-confidence advisor output cannot approve a change.
- If advisors disagree, summarize the disagreement and request user decision.
- Preserve the original locked spec and record the amendment decision.

## Output

Produce a handoff object in `phase: amend` with `status: needs-user`, unless the issue is proven to be non-spec implementation work.

For the exact amendment contract, read `references/amendment-contract.md`.
