# Driftlock

Adaptive SDD harness for long-horizon coding agents.

**Tagline:** Lock product intent before agents write code.

Driftlock is a Codex plugin and skill set for turning product intent into a locked, testable spec before implementation starts. Execution stays small by default, then escalates to Debug, CE, amendment advisors, or additional review only when gates fail.

## Core Flow

1. Spec Lock Loop: intent -> brainstorm -> grill-me -> spec gates -> locked spec
2. Task Split Gate: validate coverage, dependencies, and task-level acceptance criteria
3. Execution Loop: implement -> build/test -> review -> gate
4. Conditional Escalation: build failures trigger Debug; review rejects may trigger CE
5. Amendment Advisor: spec-impacting conflicts go through model advice and user approval
6. Final Handoff: only after task gates and integration gate pass

## Plugin Skills

- `driftlock-spec-lock`: turn user intent into a locked spec.
- `driftlock-execute`: run gated implementation from a locked spec.
- `driftlock-amend`: handle spec conflicts with advisor fallback and user approval.
- `driftlock-compound`: capture repeated failures and update learning notes.

## Minimal Code Layer

The Markdown skills define behavior. The scripts provide deterministic safety:

- Gate validation
- Retry and escalation state
- Structured handoff records
- Advisor fallback routing
- Dry-run workflow verification

## Quick Commands

```powershell
$py = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"

& $py .\scripts\driftlock.py validate locked-spec .\templates\locked-spec.json
& $py .\scripts\driftlock.py validate tasks .\templates\tasks.json --spec .\templates\locked-spec.json
& $py .\scripts\driftlock.py validate handoff .\templates\handoff.json
& $py .\scripts\driftlock.py dry-run --out .\.driftlock\dry-run
```

Official Codex validation:

```powershell
& $py "$env:USERPROFILE\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py" .
& $py "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .\skills\driftlock-spec-lock
& $py "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .\skills\driftlock-execute
& $py "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .\skills\driftlock-amend
& $py "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .\skills\driftlock-compound
```

## Status

Local-first implementation. GitHub remote is intentionally deferred.
