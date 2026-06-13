# Lodestar Third-Party Notices

Lodestar vendors selected reference material to build a completeness-first AI
development harness. Vendored sources are kept under `third_party/upstream/` and
are not exposed as first-class Lodestar plugin skills unless explicitly adapted
into `skills/lodestar-*`.

This notice is not legal advice. It records the upstream attributions that must
remain with substantial copied portions of the referenced projects.

## Vendored References

### GitHub Spec Kit

- Source: https://github.com/github/spec-kit
- Vendored commit: `7106858c4e636098815fffa23f6c6b99eb0e156b`
- License: MIT
- Copyright: GitHub, Inc.
- Local root: `third_party/upstream/spec-kit/`

### Superpowers

- Source: https://github.com/obra/superpowers
- Vendored commit: `6fd4507659784c351abbd2bc264c7162cfd386dc`
- License: MIT
- Copyright: Copyright (c) 2025 Jesse Vincent
- Local root: `third_party/upstream/superpowers/`

### Compound Engineering Plugin

- Source: https://github.com/EveryInc/compound-engineering-plugin
- Vendored commit: `b6250490bec4c0488d68ad66d72bd99f6edb95fd`
- License: MIT
- Copyright: Copyright (c) 2025 Every
- Local root: `third_party/upstream/compound-engineering-plugin/`

### gstack

- Source: https://github.com/garrytan/gstack
- Vendored commit: `d8c91c6267517c639bd338197368ffd2c2b60be2`
- License: MIT
- Copyright: Copyright (c) 2026 Garry Tan
- Local root: `third_party/upstream/gstack/`

## Lodestar Adaptation Policy

- Keep upstream source material traceable by repository, commit, license, and
  local path.
- Do not expose upstream skill names directly from the Lodestar plugin
  manifest. Lodestar exposes only `lodestar-*` skills.
- Adapt upstream behavior into Lodestar contracts, validators, and runner
  states rather than executing foreign harness preambles directly.
- Preserve original licenses and copyright notices for all substantial copied
  portions.
