---
description: Load vault context at session start — what was last in motion, what's blocked, what's next
---

You're invoking the **vault orient** routine. The user is starting (or returning to) a session and wants you primed with the current state of their Obsidian vault before any work begins.

The vault root is from CLAUDE.md context (e.g., `~/obsidian/myvault/`); the LLM-managed area is `<vault-root>/llmzone/`. If you haven't already this session, **read `llmzone/START_HERE.md` and `llmzone/shared/SKILL.md`** before continuing.

## Steps

1. **Read `llmzone/work/00_index/Active_Work.md`** for the current list of active features and notes.

2. **List recent session logs**: `ls -t llmzone/work/40_logs/sessions/*.md | head -5`. Read the most recent 1-2 to surface what was last in motion.

3. **List recent daily logs** if any: `ls -t llmzone/work/40_logs/daily/*.md | head -3`.

4. **For each active feature in `10_projects/<Feature>_<MonYY>/`**, glance at:
   - the parent algorithm note(s) — read `## Open Questions` and the `**Status**` badge
   - any in-flight PRs (look at their `status:` field; flag anything Open or Proposed)
   - the runbook's `date:` (flag if older than 30 days)

5. **Run a quick health check**: `python3 llmzone/shared/scripts/vault.py check --no-gh 2>&1 | tail -15`. Surface any non-clean findings.

6. **Summarize for the user** in 5–8 bullet points:
   - **In flight**: what feature(s) are active and at what status
   - **Last session**: what was being worked on and where you left off
   - **Open questions**: pull from the most active feature's algorithm notes
   - **Blockers / staleness**: anything `vault check` flagged, stale runbooks, deferred decisions
   - **Suggested next move**: based on the above, what looks like the natural thing to pick up

## Notes

- This is read-only — don't write to the vault during orient. The user may direct you elsewhere after seeing the summary.
- If the vault is empty (no features, no logs), say so plainly and suggest `vault new feature <Name>` as the natural starting point.
- Don't dump full note contents; summarize. Cite wikilinks for anything the user might want to open.
