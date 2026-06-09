# Driftlock

Completeness-first UX-first AI development delegation harness.

**Tagline:** Approve product shape before agents write code.

Driftlock helps a non-developer product owner delegate implementation to AI agents without having to understand the whole internal workflow. It uses 20 first-class skills plus a reference-grade harness layer built from selected Spec Kit, Superpowers, Compound Engineering, and gstack contracts.

Internal complexity is allowed when it improves correctness, recovery, proof, and final product quality. The user-facing surface remains small: decision cards, UX approval, amendment approval, and final proof.

## Core Flow

1. Discovery: office hours -> brainstorm -> grill -> intent brief.
2. Decision/UX: decision classify -> decision card -> design-system-lite -> UX preview -> UX approval -> UX guard.
3. Lock/Plan: product lock -> spec gate -> task split.
4. Execution Roles: implementer -> builder -> reviewer -> fixer.
5. Escalation/Delivery: amend advisor -> compound -> handoff.

## Plugin Skills

- Discovery: `driftlock-office-hours`, `driftlock-brainstorm`, `driftlock-grill`, `driftlock-intent-brief`
- Decision/UX: `driftlock-decision-classify`, `driftlock-decision-card`, `driftlock-design-system-lite`, `driftlock-ux-preview`, `driftlock-ux-approval`, `driftlock-ux-guard`
- Lock/Plan: `driftlock-product-lock`, `driftlock-spec-gate`, `driftlock-task-split`
- Execution Roles: `driftlock-implementer`, `driftlock-builder`, `driftlock-reviewer`, `driftlock-fixer`
- Escalation/Delivery: `driftlock-amend-advisor`, `driftlock-compound`, `driftlock-handoff`

## Minimal Code Layer

The Markdown skills define the agent workflow. `scripts/driftlock.py` provides deterministic safety:

- Upstream registry validation
- Completeness-first run initialization under `.driftlock/runs/<run-id>/`
- Product lock and Locked Spec validation
- Task coverage validation
- Runner transition validation
- Role and escalation safety checks
- Quality/QA gate validation
- Advisor fallback routing
- Proof bundle validation
- Dry-run workflow verification

## Vendored References

Selected upstream reference material lives under `third_party/upstream/` and is
mapped in `references/upstream-map.json`.

- Spec Kit: spec templates, command templates, setup scripts
- Superpowers: brainstorming, planning, worktrees, subagent execution, TDD, debugging, verification, review/finish flow
- Compound Engineering: code review, debug, proof, browser test, worktree, compound learning
- gstack: office-hours, CEO/engineering/design review, design HTML/review, QA, ship, guard, learn, context, health

Upstream skills are not exposed directly. Driftlock exposes only `driftlock-*`
skills and adapts upstream behavior through references, validators, and runner
states.

## Artifact Contract

- `intent-brief.md`
- `decision-card.json`
- `design-system-lite.md`
- `ux-preview.html`
- `ux-lock.md`
- `locked-spec.json`
- `decision-log.jsonl`
- `spec-gate-report.json`
- `task-graph.json`
- `execution-plan.json`
- `tasks/<task-id>/state.json`
- `build-evidence.json`
- `review-report.json`
- `browser-evidence.json`
- `quality-report.json`
- `amendment-request.json`
- `ce-synthesis.json`
- `ce-brief.md`
- `proof-bundle.json`
- `final-handoff.json`

## Quick Commands

macOS/Linux:

```bash
cd ~/driftlock
python3 -m venv .venv
. ./.venv/bin/activate
python -m pip install -r requirements-dev.txt
chmod +x ./scripts/driftlock

./scripts/driftlock validate locked-spec ./templates/locked-spec.json
./scripts/driftlock validate task-graph ./templates/task-graph.json --spec ./templates/locked-spec.json
./scripts/driftlock spec-gate --spec ./templates/locked-spec.json --ux-lock ./templates/ux-lock.md --decision-log ./templates/decision-log.jsonl --out ./.driftlock/spec-gate-smoke.json
./scripts/driftlock validate spec-gate-report ./.driftlock/spec-gate-smoke.json
./scripts/driftlock execution-start --task-graph ./templates/task-graph.json --spec ./templates/locked-spec.json --run-id example-run --run-dir ./.driftlock/runs/example-run
./scripts/driftlock execution-dispatch-batch --task-graph ./templates/task-graph.json --spec ./templates/locked-spec.json --run-dir ./.driftlock/runs/example-run --out ./.driftlock/runs/example-run/dispatch/agent-dispatch-batch.json
./scripts/driftlock validate agent-dispatch-batch ./.driftlock/runs/example-run/dispatch/agent-dispatch-batch.json
./scripts/driftlock validate execution-plan ./.driftlock/runs/example-run/execution-plan.json
./scripts/driftlock upstream-check
./scripts/driftlock negative-checks --skills-dir ./skills
./scripts/driftlock dry-run --out ./.driftlock/dry-run
./scripts/driftlock quality-gate --run-dir ./.driftlock/dry-run --browser-evidence ./.driftlock/dry-run/browser-evidence.json --out ./.driftlock/quality-smoke.json
./scripts/driftlock ce-synthesize --run-dir ./.driftlock/dry-run --out ./.driftlock/ce-smoke.json --brief-out ./.driftlock/ce-smoke.md
```

Windows PowerShell:

```powershell
$py = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"

& $py .\scripts\driftlock.py validate locked-spec .\templates\locked-spec.json
& $py .\scripts\driftlock.py validate task-graph .\templates\task-graph.json --spec .\templates\locked-spec.json
& $py .\scripts\driftlock.py validate build-evidence .\templates\build-evidence.json
& $py .\scripts\driftlock.py validate review-report .\templates\review-report.json
& $py .\scripts\driftlock.py browser-collect --html .\templates\ux-preview.html --expect-text "Product Shape Preview" --out .\.driftlock\browser-smoke.json
& $py .\scripts\driftlock.py validate browser-evidence .\.driftlock\browser-smoke.json
# Optional when a real browser tool already captured rendered DOM/console/screenshot:
# & $py .\scripts\driftlock.py browser-collect --snapshot .\templates\browser-snapshot.json --expect-text "Product Shape Preview" --out .\.driftlock\browser-evidence.json
& $py .\scripts\driftlock.py validate amendment-request .\templates\amendment-request.json
& $py .\scripts\driftlock.py spec-gate --spec .\templates\locked-spec.json --ux-lock .\templates\ux-lock.md --decision-log .\templates\decision-log.jsonl --out .\.driftlock\spec-gate-smoke.json
& $py .\scripts\driftlock.py validate spec-gate-report .\.driftlock\spec-gate-smoke.json
& $py .\scripts\driftlock.py execution-start --task-graph .\templates\task-graph.json --spec .\templates\locked-spec.json --run-id example-run --run-dir .\.driftlock\runs\example-run
& $py .\scripts\driftlock.py execution-dispatch-batch --task-graph .\templates\task-graph.json --spec .\templates\locked-spec.json --run-dir .\.driftlock\runs\example-run --out .\.driftlock\runs\example-run\dispatch\agent-dispatch-batch.json
& $py .\scripts\driftlock.py execution-next --run-dir .\.driftlock\runs\example-run
& $py .\scripts\driftlock.py validate agent-dispatch .\.driftlock\runs\example-run\dispatch\T1-agent-dispatch.json
& $py .\scripts\driftlock.py validate agent-dispatch-batch .\.driftlock\runs\example-run\dispatch\agent-dispatch-batch.json
& $py .\scripts\driftlock.py execution-status --run-dir .\.driftlock\runs\example-run
& $py .\scripts\driftlock.py validate execution-plan .\.driftlock\runs\example-run\execution-plan.json
& $py .\scripts\driftlock.py validate quality-report .\templates\quality-report.json
& $py .\scripts\driftlock.py validate ce-synthesis .\templates\ce-synthesis.json
& $py .\scripts\driftlock.py validate final-handoff .\templates\final-handoff.json
& $py .\scripts\driftlock.py validate proof-bundle .\templates\proof-bundle.json
& $py .\scripts\driftlock.py upstream-check
& $py .\scripts\driftlock.py init-run --run-id example-run
& $py .\scripts\driftlock.py runner-step --state .\.driftlock\runner.json --event office-hours-pass --evidence "office hours complete"
& $py .\scripts\driftlock.py negative-checks --skills-dir .\skills
& $py .\scripts\driftlock.py dry-run --out .\.driftlock\dry-run
& $py .\scripts\driftlock.py quality-gate --run-dir .\.driftlock\dry-run --browser-evidence .\.driftlock\dry-run\browser-evidence.json --out .\.driftlock\quality-smoke.json
& $py .\scripts\driftlock.py ce-synthesize --run-dir .\.driftlock\dry-run --out .\.driftlock\ce-smoke.json --brief-out .\.driftlock\ce-smoke.md
```

Official Codex validation:

macOS/Linux:

```bash
cd ~/driftlock
. ./.venv/bin/activate
python ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
for skill in ./skills/*; do
  [ -d "$skill" ] || continue
  python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py "$skill"
done
```

Windows PowerShell:

```powershell
& $py "$env:USERPROFILE\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py" .
Get-ChildItem .\skills -Directory | ForEach-Object {
  & $py "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" $_.FullName
}
```

## Status

Local-first implementation. GitHub remote exists separately and can be updated after local validation.
