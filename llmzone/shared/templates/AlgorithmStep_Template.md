---
type: algorithm-step
scope: work
feature: <FeatureName>
area: <subsystem>
date: YYYY-MM-DD
status: Proposed              # Proposed | Implemented | Deferred | Reverted | Superseded — usually mirrors parent
parent: <ParentAlgorithmName>  # used by index_rebuild.py to associate with parent
tags: [<feature>, <area>, algorithm-step]
---

# AlgorithmStep_Template

Parent: [[llmzone/work/10_projects/<FeatureName>_<MonYY>/algorithms/<ParentAlgorithmName>]]

## Goal

What this step produces from what inputs.

## Code entry points

- `Function::name` — [`file.cpp:NN`](https://github.com/<owner>/<repo>/blob/<sha>/path/file.cpp#LNN)
- (use `permalink_rewrite.py` to convert plain `file.cpp:NN` references)

## Walkthrough

1. Numbered prose describing what the step does.
2. Permalink to source at decision points.
3. Cite specific functions for the reader to follow along.

## Configs touched

- `field.name` — default value, what controls
- (add per config field this step reads/writes)

## Edge cases / known issues

- Magic numbers
- Dead branches in this caller
- Undocumented invariants the step relies on

## Open Questions

- Questions specific to this step.

## Feeds

[[Step<X+1>_<Next>]] — what data structure this hands off.
