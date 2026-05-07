---
description: Draft a PR summary note for a given PR number — fetches diff/title/discussion via gh, fills the template
argument-hint: <pr-number> [<feature>]
---

You're drafting a **PR summary note** for the user's vault. The argument is the PR number (and optionally the feature it belongs to).

The vault root is from CLAUDE.md context; the LLM-managed area is `<vault-root>/llmzone/`. If you haven't this session, **read `llmzone/START_HERE.md` and `llmzone/shared/SKILL.md`** first — pay particular attention to the PR-summary section requirements (Context, Change, Why, Validation, Known Gaps).

## Steps

1. **Parse the arguments** ($ARGUMENTS): first token = PR number (required), second token = feature name (optional). If feature isn't given, infer from the PR title/branch (e.g. branch `shreyas/<feature-keyword>-foo` → look for matching feature dir under `10_projects/`). If you still can't tell, ask the user before proceeding.

2. **Fetch PR data via gh**:
   - `gh pr view <num> --json number,title,body,state,isDraft,mergedAt,closedAt,headRefName,url,baseRefName,additions,deletions`
   - `gh pr diff <num>` — capture the diff. If it's huge (>500 lines), `gh pr diff <num> | head -300` plus a `git log` summary; you don't need every line.
   - `gh pr view <num> --comments` — review thread, useful for capturing decisions made in review.

3. **Decide the kebab-topic** for the filename: derive from the PR title (lowercase, kebab-case, drop article words). Sanity-check with the user if the title is opaque.

4. **Create the note**: `python3 llmzone/shared/scripts/vault.py new pr <feature> <pr-number> <kebab-topic> --repo <owner>/<repo>` — this auto-fills frontmatter from `gh pr view` (title, branch, status, URL).

5. **Fill the body**: read the diff and the PR description, then write the body sections. Required:
   - **Context** — the problem the PR addresses, scope boundaries, non-goals (extract from PR description if present, fill gaps from the diff)
   - **Change** — core implementation changes / validation guards / behavior changes (group by purpose, not by file)
   - **Why** — approach taken + tradeoffs accepted (often in PR description; fill if absent)
   - **Validation** — build commands + test commands. If the PR description doesn't list these, look at the diff for changed test files and `cmake`/`ctest` patterns; otherwise leave the template's `<command>` placeholders for the user to fill
   - **Known Gaps** — unimplemented follow-ups; pull from the PR's "TODO" mentions or "future work" sections
   - Optionally: **Open Questions** if the PR description mentions unresolved items

6. **Set cross-refs in frontmatter** if you can identify them:
   - `algorithms: [<NameOfAlgorithmTouched>]` — match changed code files against existing algorithm notes' "Implementation refs" sections
   - `decisions: [<decision-filename>]` — only if the PR explicitly references a decision note

7. **Convert any backticked code refs to permalinks**: if you cite `file.cpp:NN` in the body, use `permalink_rewrite.py` to pin to the PR's merge SHA (or HEAD if still open).

8. **Run rebuild**: `python3 llmzone/shared/scripts/vault.py rebuild`. Confirm no warnings.

9. **Print the note path** to the user with a short summary of what you wrote and any sections that still need their input (e.g. "I left Validation commands as placeholders since the PR description didn't include them").

## Notes

- Don't fabricate validation commands or test names you didn't see — leave the template placeholders if uncertain.
- If the PR is still Open / Draft, status auto-fills accordingly; the note can be updated via `vault rebuild --gh-sync` once the PR merges.
- For very large PRs, prefer summarizing the diff (group changes by purpose) over enumerating every file.
- If `gh` isn't available, fall back to asking the user for title/branch/URL and fill the body from the diff alone.
