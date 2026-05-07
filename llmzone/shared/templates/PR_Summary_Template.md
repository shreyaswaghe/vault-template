---
type: pr-summary
scope: work
feature: <FeatureName>
area: <subsystem>
date: YYYY-MM-DD
pr: <number>
branch: <branch-name>
status: Open                  # Proposed | Open | Merged | Reverted | Closed
algorithms: []                 # algorithm notes this PR touches
decisions: []                  # decision notes this PR implements
reverts: []                    # PR numbers this PR reverts, e.g. [4721]
tags: [<feature-lowercase>, pr-summary]
---

# PR_Summary_Template

> Before filling this template, review [[llmzone/shared/SKILL]] and [[llmzone/shared/Pre_Edit_Checklist]].

<!-- AUTOGEN:status START -->
<!-- AUTOGEN:status END -->

One sentence: what this PR changes.

## PR

- PR: [#<number>](<url>)
- Branch: `<branch-name>`

## Context

- Problem this PR addresses
- Scope boundaries
- Non-goals

## Change

- Core implementation changes
- Validation/guardrail changes
- Behavior changes (if any)

## Why

- Approach chosen
- Tradeoffs accepted

## Validation

- Build:
  - `<command>`
- Tests:
  - `<command>`
- Result: pass/fail + short evidence summary

## Known Gaps

- Unimplemented follow-ups
- Edge cases not covered yet

## Next Steps

- [ ] Follow-up item

## Open Questions

Unresolved at PR time.

## Related

<!-- AUTOGEN:related START -->
<!-- AUTOGEN:related END -->
