---
description: Re-pin GitHub permalinks in vault notes to a fresh commit SHA, surfacing any that no longer resolve
argument-hint: [<note-stem-or-path>]
---

You're invoking **vault permalinks refresh**. Existing notes pin code references to specific commit SHAs; over time SHAs age and the linked code may have moved or been deleted. This command refreshes SHAs to the current HEAD of the relevant code repo and surfaces any links that broke.

The vault root is from CLAUDE.md context; the LLM-managed area is `<vault-root>/llmzone/`. **Read `llmzone/shared/SKILL.md`** (the GitHub permalinks rule) if you haven't this session.

## Steps

1. **Determine scope**: $ARGUMENTS optionally names a note (stem or path). If empty, refresh permalinks across all active notes under `<vault-root>/llmzone/work/10_projects/`. (Archive notes are intentionally left frozen — they're historical.)

2. **Identify the code repo(s)** referenced in the targeted notes. The repo is encoded in each permalink as `github.com/<owner>/<repo>/blob/<sha>/...`. A single note may pin to one repo; the whole vault may pin to several.

3. **For each repo**, find the local clone:
   - Ask the user for the path if you don't already know.
   - `cd <repo-path> && git fetch origin` to ensure HEAD is fresh.
   - Capture the new SHA: `git rev-parse origin/main` (or `origin/master` — check `git symbolic-ref refs/remotes/origin/HEAD` for the actual default branch).

4. **Run staleness verification first**: `python3 <vault-root>/llmzone/shared/scripts/verify_permalinks.py --repo <owner>/<repo> --repo-root <path> --ref <branch> <target-paths>`. This reports four categories:
   - `PATH-MOVED-OR-DELETED` — file no longer at that path
   - `LINES-OUT-OF-RANGE` — file shorter than the linked range
   - `SYMBOL-MISSING` / `SYMBOL-DRIFTED` — heuristic symbol checks (less reliable)

5. **For PATH-MOVED / LINES-OUT-OF-RANGE findings**: ask the user per finding —
   - **Re-pin**: rewrite the link to a new path/range that still represents the same code (you'll need to find where the code moved to)
   - **Delete the citation**: if the code is gone and the note's claim is stale, edit the surrounding prose
   - **Skip**: keep the stale link with a comment, in cases where preserving the historical reference matters

6. **For clean notes (no path/lines failures)**: bulk-update the SHA via `sed`-style rewrite, replacing the old SHA with the new one across the targeted files:
   ```
   find <target-paths> -name "*.md" -exec sed -i \
       "s|github.com/<owner>/<repo>/blob/<old-sha>|github.com/<owner>/<repo>/blob/<new-sha>|g" {} +
   ```
   Apply per old-SHA-found, since a note may pin different sections to different SHAs intentionally.

7. **Re-run `verify_permalinks.py`** at the new SHA to confirm everything still resolves.

8. **Run `permalink_rewrite.py`** to convert any plain `file.cpp:NN` references in the targeted notes (the user may have written some since last refresh):
   ```
   python3 <vault-root>/llmzone/shared/scripts/permalink_rewrite.py \
       --sha <new-sha> --repo <owner>/<repo> --repo-root <repo-path> \
       <target-files>
   ```

9. **Run `vault rebuild`** to refresh autogen sections (Status badges may pick up date changes if you updated `date:` fields).

10. **Print summary**:
    - Notes updated, with old → new SHA per repo
    - Per-note breakdown of refresh decisions (re-pinned, deleted citation, skipped)
    - Any remaining `verify_permalinks.py` warnings the user should review

## Notes

- Refreshing the SHA without checking validity is dangerous — a clean SHA bump can mask references that silently moved to a different file. `verify_permalinks.py` is the safety net; don't skip it.
- For a single targeted note (`/vault-permalinks-refresh <stem>`), this is fast — handle it inline. For the whole vault, expect a longer interactive session.
- If the repo's local clone isn't fresh (`git status` shows uncommitted work or detached HEAD), fetch from origin and pick a known ref like `origin/main` rather than the local HEAD, which may be in an arbitrary state.
- This is read-only on the *code* side — never push, never modify files in the code repo. Only the vault notes change.
