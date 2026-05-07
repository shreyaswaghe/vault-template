---
type: template
scope: shared
zone: llmzone
status: active
tags: [llmzone, cleanup, checklist, template]
---

# Cleanup_Run_Checklist_Template

## Run Metadata

- Date:
- Cadence: `weekly` / `monthly`
- Operator:

## Safety Gate

- [ ] No unresolved git conflicts in vault files
- [ ] Cleanup scope is clear
- [ ] No large restructure required

## Core Checks

- [ ] Notes are in correct scope folders
- [ ] Required frontmatter exists (`type`, `scope`, `status`, `tags`)
- [ ] `Active_Work` updated
- [ ] Hub links added/fixed for new notes
- [ ] Duplicate canonicals merged or replaced with pointer notes
- [ ] Authoritative discussion kept in `llmzone/**`

## Monthly-Only Checks

- [ ] Stale done notes archived to `50_archive`
- [ ] Near-duplicate tags normalized
- [ ] MOCs refreshed for discoverability
- [ ] `SKILL.md` updated if repeated issue observed

## Outcomes

- Updated notes:
- Archived notes:
- Pointer notes created:
- Follow-ups (`status: needs-review`):
