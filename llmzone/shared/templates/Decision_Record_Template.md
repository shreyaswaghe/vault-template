---
type: decision
scope: work
feature: <FeatureName>
area: <subsystem>
date: YYYY-MM-DD
status: Proposed              # Proposed | Accepted | Deprecated | Superseded
superseded_by:                 # filename (without .md) of newer decision that replaces this one
algorithms: []                 # algorithms this decision affects
prs: []                        # PRs that implement this decision
tags: [<feature-lowercase>, decision]
---

# Decision_Record_Template

> Before filling this template, review [[llmzone/shared/SKILL]] and [[llmzone/shared/Pre_Edit_Checklist]].

<!-- AUTOGEN:status START -->
<!-- AUTOGEN:status END -->

One sentence: what is being decided.

## Context

What forced this decision: prior state, constraints, what breaks without one. 1-3 paragraphs.

## Options considered

### Option A — <name>

Short summary.

- **Pros**: ...
- **Cons**: ...

### Option B — <name>

Short summary.

- **Pros**: ...
- **Cons**: ...

(For trivial decisions where alternatives are obvious: a one-line "Considered: <X>, dismissed because <Y>" is acceptable.)

## Decision

One short paragraph: what was chosen and the load-bearing reason.

## Consequences

What changes downstream: code, conventions, behavior, what becomes easier/harder, explicit follow-ups.

## Open Questions

Unresolved at decision time.

## Related

<!-- AUTOGEN:related START -->
<!-- AUTOGEN:related END -->
