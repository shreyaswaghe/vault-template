---
type: runbook
scope: work
feature: <FeatureName>
area: <subsystem>
date: YYYY-MM-DD              # date last verified working
status: Active                # Active | Outdated | Deprecated
algorithms: []                 # algorithms this runbook exercises (empty = exercises feature broadly)
tags: [<feature-lowercase>, runbook]
---

# Runbook_Template

> Before filling this template, review [[llmzone/shared/SKILL]] and [[llmzone/shared/Pre_Edit_Checklist]].

<!-- AUTOGEN:status START -->
<!-- AUTOGEN:status END -->

One sentence: what this runbook helps you build and test.

## Prerequisites

- Working directory: `/path/to/build/dir`
- Branch / commit assumptions
- Env vars or dependencies that must be present

## Build

```bash
<targeted build command>
```

Expected: <where binaries land, what artifact to look for>.

## Test

```bash
<targeted test command, e.g. ctest -R "<pattern>" --output-on-failure>
```

Expected: <pass criteria, where logs go>.

## Common failures

(grow this organically — empty on day 1 is fine)

- **Symptom**: ...
  - **Fix**: ...

## Open Questions

Unresolved at last update.

## Related

<!-- AUTOGEN:related START -->
<!-- AUTOGEN:related END -->
