---
description: Inspect current git diff and surface vault notes that need writing or updating
---

You're invoking the **from-diff sweep**: looking at uncommitted/recent code changes in the user's current repository, identify which vault notes are stale or missing. Read-only — surface gaps, don't write.

The vault root is from CLAUDE.md context; the LLM-managed area is `<vault-root>/llmzone/`. **Read `llmzone/START_HERE.md` and `llmzone/shared/SKILL.md`** if you haven't this session.

## Steps

1. **Confirm you're in a code repo, not the vault**: `git rev-parse --show-toplevel`. If the user is sitting in their vault dir, ask which code repo they want analyzed.

2. **Capture the change context** in this code repo:
   - `git status` — branch, staged + unstaged changes
   - `git diff` — uncommitted changes (working tree + index)
   - `git log -10 --oneline` — recent commits, in case work has already been committed
   - If a PR is open for the current branch, `gh pr view` to get its description

3. **Build a list of changed files** with a one-line summary of what each change is (added/modified/deleted; added function names; etc.). Group by directory or subsystem if there are many.

4. **Cross-reference against the vault**:
   - For each changed code file, grep `<vault-root>/llmzone/work/10_projects/` for notes that cite it in their `## Implementation refs` section. List which notes touch this file.
   - Look up `<vault-root>/llmzone/work/00_index/Active_Work.md` for the list of active features. Do the changed files match an existing feature, or is this work for a feature that doesn't have a vault entry yet?

5. **Identify gaps** — categorize each as:
   - **Missing PR summary**: there are committed changes (via `git log`) but no PR note for them in `prs/`. Suggest `/vault-pr-summary <num>` if a PR exists, or `vault new pr` once one is opened.
   - **Stale algorithm note**: changed file matches an existing algorithm's Implementation refs, but the diff materially changes the pipeline (added/removed stages, changed key configs). Flag the note for an update.
   - **Stale permalinks**: existing notes reference SHAs in this file that the diff makes obsolete. Suggest `permalink_rewrite.py` after the changes land.
   - **Missing decision**: the diff implies a non-trivial design choice (replacing X with Y, switching algorithms, changing a default) and there's no decision note for it. Suggest `vault new decision`.
   - **Missing feature**: changed files don't match any active feature dir. Suggest `vault new feature <Name>`.

6. **Output**: a structured report — one section per gap category, each gap with:
   - The vault note (or "(missing)") that's affected
   - One-line reasoning citing the specific change
   - The exact `vault` / slash-command invocation to address it

7. **Don't auto-write anything**. The user decides which gaps to act on.

## Notes

- Be conservative on "stale algorithm" — most diffs are small and don't materially change the pipeline. Only flag if you see clear additions/removals to stages, configs, or invariants the algorithm note documents.
- If the diff is huge (e.g. a refactor branch), summarize at file granularity rather than line-by-line; the goal is gap detection, not code review.
- If the user is already on a feature branch with a corresponding feature dir, scope your report to that feature.
- Run `vault check` afterwards if any of your suggestions involve cross-refs the user might want to verify.
