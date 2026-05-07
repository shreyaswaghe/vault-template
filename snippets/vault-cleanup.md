---
description: Drive the vault cleanup playbook interactively (weekly or monthly)
argument-hint: [weekly|monthly]
---

You're invoking **vault cleanup**. The user wants to run the weekly or monthly cleanup routine semi-interactively — you do the mechanical bits (`vault check`, walking the indices), they make the human calls (archive this? merge these tags? defer this?).

The vault root is from CLAUDE.md context; the LLM-managed area is `<vault-root>/llmzone/`. **Read `llmzone/shared/LLM_Cleanup_Playbook.md` and `llmzone/shared/SKILL.md`** if you haven't this session.

## Steps

1. **Decide cadence**: $ARGUMENTS = `weekly` (10–15 min) or `monthly` (30 min). If absent, ask the user.

2. **Baseline check**: run `python3 <vault-root>/llmzone/shared/scripts/vault.py check` and capture all findings. Group them by category for the routine below.

3. **Walk Active_Work** (always): read `<vault-root>/llmzone/work/00_index/Active_Work.md`. For each active feature, ask the user:
   - "Is `<feature>` still in motion, or done/deferred?"
   - If done → suggest archiving its remaining notes (`vault archive <stem>` per note); confirm before each.
   - If deferred → flip relevant algorithm/runbook `status:` to `Deferred` (manual frontmatter edit; warn the user the script doesn't auto-revert this).

4. **Process check findings interactively**:
   - **Dangling wikilinks**: for each, ask the user — fix the typo, delete the link, or create the missing note?
   - **Missing TL;DR**: propose a one-sentence TL;DR for each based on the note's body, ask the user to approve or revise, then write it.
   - **Missing `feature:` frontmatter**: propose a value based on the note's path/content, ask, write.
   - **Stale runbooks**: for each, ask "did you re-run the commands? do they still work?" If yes, update `date:` to today. If no, ask whether to flip `status: Outdated` or fix and re-verify.

5. **Weekly run** (stop here):
   - Run `vault rebuild --gh-sync` to refresh PR statuses from GitHub.
   - Run `vault check` again to confirm clean.
   - Print summary of what was changed.

6. **Monthly run** (continues after step 5):
   - **Archive sweep**: walk `50_archive/` — anything obviously stale or duplicated? (Rare; usually nothing to do.)
   - **Tag normalization**: run `grep -rho 'tags: \[.*\]' <vault-root>/llmzone/work/ | sort | uniq -c | sort -rn` and look for near-duplicate tags (e.g. `gai` vs `gai-mesher`, `pr` vs `pr-summary`). For each pair, ask the user which canonical form to keep; rewrite the others.
   - **Permalink staleness**: run `python3 <vault-root>/llmzone/shared/scripts/verify_permalinks.py --repo <repo> --repo-root <path> <vault-root>/llmzone/work/10_projects/`. For each `PATH-MOVED` or `LINES-OUT-OF-RANGE` finding, ask the user whether to re-pin to a newer SHA or rewrite the surrounding text.
   - **SKILL retro**: ask "did the same kind of issue come up multiple times this month? Should we add a rule to SKILL.md to prevent it?"
   - Run `vault rebuild` once more, then `vault check` — confirm clean.

7. **Wrap up**: print a structured changelog of everything you and the user changed during the cleanup, suitable for the user to skim as a session record.

## Notes

- Don't make irreversible changes without explicit user confirmation per item. Bulk operations ("delete all stubs", "rewrite all tags") are too risky.
- If `vault check` was already clean coming in and Active_Work is settled, say so plainly and skip to a one-line "nothing to do this run." Don't manufacture work.
- The output of this command should ideally be saved as a session log: `vault new` doesn't have a `cleanup` type, so use a regular log file under `40_logs/sessions/YYYY-MM-DD_cleanup-{weekly|monthly}.md` if the run produced material changes.
- This command is destructive when the user agrees — be careful, double-check before each `vault archive` invocation.
