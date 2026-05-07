---
type: index
zone: llmzone
status: active
tags: [llmzone, conventions, scope]
---

# Tags_and_Conventions

Authoritative conventions live in [[llmzone/shared/SKILL]]. This page is a quick-reference summary.

## Required frontmatter (per-type quick reference)

Every note: `type`, `scope`, `date`, `status`, `tags`.

For project notes (anything under `10_projects/<feature>/` or `50_archive/<feature>/`), also: `feature`, optional `area`.

Type-specific extras:

```yaml
---
# algorithm
type: algorithm
scope: work
feature: <FeatureName>
area: <subsystem>             # optional
date: YYYY-MM-DD
status: Proposed              # Proposed | Implemented | Deferred | Reverted | Superseded
prs: []                       # PR numbers that implement this algorithm
decisions: []                 # decision filenames (without .md) this algorithm obeys
supersedes:                   # name of an older algorithm this replaces
tags: [<feature-lowercase>, algorithm]
---
```

```yaml
---
# pr-summary
type: pr-summary
scope: work
feature: <FeatureName>
date: YYYY-MM-DD
pr: <number>
branch: <branch-name>
status: Open                  # Proposed | Open | Merged | Reverted | Closed
algorithms: []
decisions: []
reverts: []                   # PR numbers this PR reverts
tags: [<feature-lowercase>, pr-summary]
---
```

See [[llmzone/shared/SKILL]] for the other types and the full status-derivation rules.

## Naming

- Algorithm: `PascalCase.md`
- Algorithm step: `Step<N>_PascalCase.md` (digit, not letter, for sortability)
- Decision: `YYYY-MM-DD_kebab-topic.md`
- PR summary: `YYYY-MM-DD_pr-<num>_kebab-topic.md`
- Runbook (canonical): `Build_and_Test_<FeatureName>.md`
- Feature dir: `<FeatureName>_<MonYY>` (e.g. `MyFeature_Apr26`)

## Scope boundary rules

- Work notes must live under `llmzone/work/**`.
- Personal notes must live under `llmzone/personal/**`.
- Shared reusable resources (templates, skills, scripts) live under `llmzone/shared/**`.
- When archiving, do **not** leave a pointer stub at the old path — the per-feature `Archived.md` (autogen) and the MoC's `## Archive` section provide discovery.
