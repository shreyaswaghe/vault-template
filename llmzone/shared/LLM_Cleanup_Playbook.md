---
type: runbook
scope: shared
zone: llmzone
date: 2026-04-07
status: active
tags: [llmzone, cleanup, compaction, llm, runbook]
---

# LLM_Cleanup_Playbook

Simple, repeatable cleanup routine for LLM-driven vault maintenance.

## Rules

- Keep changes small and reversible.
- If unsure, do not restructure; mark `status: needs-review`.
- Keep one canonical note per topic; merge duplicates rather than leaving stubs.
- Keep authoritative discussion in `llmzone/**`; code docs are references.
- When moving notes, update links in the same run, then rerun `scripts/index_rebuild.py`.

## Weekly Run (10-15 min)

- Move notes to correct scope (`work`, `personal`, `shared`) and to the right feature dir under `10_projects/<Feature>_<MonYY>/`.
- Fix missing frontmatter: `type`, `scope`, `status`, `tags`, and `feature` for project notes.
- Run `python3 llmzone/shared/scripts/index_rebuild.py` to refresh `Active_Work`, MoC, and per-feature `Archived.md`.
- Add at least one hub link from each new note to its parent algorithm / PR / decision peer.

## Monthly Run (30 min)

- Archive stale done notes by moving them to `50_archive/<feature>/<subdir>/`, setting `status: archived`, and rerunning `index_rebuild.py` (no pointer stubs at the old path).
- Merge duplicate notes on the same topic into one canonical.
- Normalize tags by merging near-duplicates.
- Add one rule to `SKILL.md` if the same cleanup issue repeats.

## Stop Conditions

- If a move would touch many folders and intent is unclear.
- If a note has conflicting ownership (`work` vs `personal`) and no context.
- If there are unresolved git conflicts in vault files.

When any stop condition triggers, stop and mark impacted notes `status: needs-review`.

## Done Criteria

- No active note is missing required frontmatter.
- `Active_Work` reflects current active work.
- No duplicate canonical notes remain for the same artifact.
- No unresolved git conflicts remain.

## Run Template

Use: [[llmzone/shared/templates/Cleanup_Run_Checklist_Template]]
