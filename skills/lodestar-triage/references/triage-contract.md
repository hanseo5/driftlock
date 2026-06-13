# Lodestar Triage Contract

## Purpose

Protect the non-developer. Make sure the user is only ever asked to decide
things a non-coder can actually own, and let the harness safely resolve
everything else.

## Required Input

- `survey.md` plus any `scout` / `shakedown` notes — the open questions raised
  during discovery.
- The run mode chosen at `/lodestar` start: `guided` or `express` (default
  `guided`).
- Existing repo and evidence that can answer a question without asking the user.

If discovery output is missing, stop and route back rather than guessing.

## Decision Classes

Classify every open decision into exactly one class.

| Class | Meaning | Examples |
| --- | --- | --- |
| `mechanical` | Implementation detail with no visible product effect; a competent engineer would just pick the standard option. | Framework/library choice, file and folder layout, date-formatting library, variable names, test runner, retry/timeout values, log format. |
| `taste` | Changes how the product looks, feels, or reads, with more than one reasonable answer. | Color and tone, copy and wording, layout density, which field appears first, empty-state message, default sort order. |
| `user-challenge` | Changes what the product *is* or *does* — scope, core flow, target user, or a business rule. | Add or drop a feature, who can sign up, free vs paid, what counts as "done", what data the product collects. |
| `safety-destructive` | Could lose data, cost money, send something externally, or is hard to reverse. | Delete or overwrite data, send email/SMS, charge a card, deploy to production, make something public, any third-party spend. |

## Owner + Default Action

- `mechanical` → owner `harness`. Auto-resolve from repo evidence or the
  standard choice. Record it; do **not** ask the user.
- `taste` → owner `user`. In **guided** mode, surface a decision card. In
  **express** mode, auto-resolve with the recommended option and log it so the
  user can review choices later.
- `user-challenge` → owner `user`. **Always** surface a decision card, in any
  mode. Never auto-resolve.
- `safety-destructive` → owner `user`. **Always** require explicit approval, in
  any mode. Never auto-resolve and never bundle with other decisions.

## Tie-Breakers

- Unsure between `mechanical` and `taste`, and the choice is cheap and
  reversible → treat as `mechanical` and auto-resolve. Do not burden the user;
  reserve questions for genuine product trade-offs.
- Unsure whether something is `safety-destructive` → treat it as
  `safety-destructive` and ask. Err toward asking only about risk, cost, and
  reversibility.
- A single decision may not be split into pieces to dodge user ownership.

## Required Output

Produce `decision-policy.json`: for each decision, its class, owner, default
action, and — for user-owned decisions — a one-line, product-language question
routed to `lodestar-call`. Carry enough evidence for `lodestar-lock` to verify
the policy.

## Gate Rules

- Mechanical choices may be auto-resolved with evidence.
- Taste choices require user approval, unless express mode pre-authorized them.
- User-challenge choices always require user approval; express mode cannot
  pre-authorize them.
- Safety/destructive choices always require explicit user approval.
- The harness and advisors may recommend, but never approve user-owned classes.

## Next Route

Route user-owned decisions to `lodestar-call`. Otherwise route to the next valid
Lodestar skill, or to `lodestar-course-correct` when product intent, UX lock, or
spec meaning would change.
