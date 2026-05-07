---
description: Persist this session's vault-worthy work — write notes, set cross-refs, run rebuild
---

You're invoking the **vault check-in** routine for the user's Obsidian vault. The vault root is whichever path the user cloned `vault-template/` into (e.g. `~/obsidian/myvault/`); the LLM-managed area is `<vault-root>/llmzone/`.

The vault rules live at `llmzone/shared/SKILL.md`. If you haven't already this session, **read it now along with `llmzone/START_HERE.md`** before doing anything else here.

## Steps

1. **Identify what should be persisted from this session.** Look back at the conversation. Persist any of:
   - **Algorithm description** — if you analyzed code and built a mental model worth keeping (especially if it'll be referenced in future sessions)
   - **Decision record** — if a non-trivial design choice was made (option A over option B, with reasons)
   - **PR summary** — if a PR was opened, merged, or substantively reviewed
   - **Runbook** — if you figured out a new build/test recipe worth saving
   - **Session log** — if the session itself is worth recording (long debugging arc, multiple decisions, etc.)

   If none of these apply, say so and skip to step 4.

2. **Create / update the notes** using `python3 llmzone/shared/scripts/vault.py new <type> <feature> <name>`. The script picks the right template, fills frontmatter, and places the file. Then edit the body to fill in real content.

   - Filename, frontmatter, and section conventions per type are in `SKILL.md`.
   - For **algorithm** notes, include implementation refs as GitHub permalinks (use `permalink_rewrite.py` if you have bare `file.cpp:NN` references).
   - For **decision** notes, document at least one rejected alternative.
   - For **PR** notes, include build + test command evidence.

3. **Set cross-references in frontmatter.** Whichever notes you created/touched, populate the relevant cross-ref lists so the script can derive bidirectional links:
   - `algorithm` notes: `prs:`, `decisions:`, `supersedes:`
   - `decision` notes: `algorithms:`, `prs:`, `superseded_by:`
   - `pr-summary` notes: `algorithms:`, `decisions:`, `reverts:`
   - `runbook` notes: `algorithms:`

4. **Run the rebuild**: `python3 llmzone/shared/scripts/vault.py rebuild`. Confirm no warnings (or surface any that look real).

5. **Summarize for the user**: list the notes you wrote/updated with their wikilinks, and note any open follow-ups (decisions still pending, runbooks still unverified, etc.).

## Notes

- Don't write notes for trivial work — a one-line bash fix doesn't need a session log.
- If the vault is git-tracked and you can see uncommitted changes, mention them but **do not commit** without the user's explicit OK.
- Never edit content between `<!-- AUTOGEN:* -->` markers; rerun the script instead.
