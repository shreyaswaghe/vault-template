---
description: Summarize vault + code-repo + GitHub activity over a recent window, suitable for standups / Slack / weekly updates
argument-hint: [<window>] [--save] [--format slack|bullets|email]
---

You're invoking **vault recap**. The user wants a summary of recent work — vault notes touched, code commits made, PRs opened/merged/reviewed, open questions still pending — formatted for sharing (standup, Slack, weekly update). Window-based, not daily-rigid.

The vault root is from CLAUDE.md context; the LLM-managed area is `<vault-root>/llmzone/`. **Read `llmzone/shared/SKILL.md`** if you haven't this session.

## Steps

1. **Parse $ARGUMENTS**:
   - First positional: window. Defaults to `1d`. Accepted forms:
     - `Nd` / `Nh` (last N days/hours)
     - `YYYY-MM-DD` (since that date, inclusive)
     - `yesterday`, `last-monday`, `last-week`, `today` (common shortcuts; resolve via `date -d "..." -I`)
   - `--save`: write the recap as a session log (default: print only)
   - `--format <slack|bullets|email>`: output style (default: `bullets`)
   - Compute a concrete `<since-date>` (ISO 8601) for the threshold using `date -d` and report it back to the user before proceeding.

2. **Vault activity** (the vault is git-tracked):
   - `cd <vault-root> && git log --since="<since-date>" --name-only --pretty=format:"%h %s%n"` — captures notes added or modified
   - Bucket the affected files by note type (read frontmatter):
     - **New / updated algorithm notes**
     - **New decisions**
     - **New PR summaries**
     - **Touched runbooks** (if `date:` was bumped, that's a verification event worth noting)
     - **New session logs**
   - For each, capture the H1 + TL;DR sentence so the recap can quote it.

3. **Code repo activity**:
   - Ask the user which code repo(s) to scan if not obvious. (Or check CLAUDE.md / cwd for hints.)
   - Per repo: `cd <repo> && git log --since="<since-date>" --author="$(git config user.email)" --pretty=format:"%h %s (%ar) [%an]"` — captures commits authored by the user
   - Group by branch / topic where possible
   - If multiple repos, list them separately

4. **GitHub PR activity** (if `gh` is available and authenticated):
   - `gh pr list --author @me --search "updated:>=<since-date>" --state all --json number,title,state,mergedAt,updatedAt,url --limit 30`
   - Bucket by state: **Merged**, **Open** (incl. Draft), **Closed without merge**, **Reviewed** (if you have access — `gh pr list --search "reviewed-by:@me updated:>=<since-date>"` if you also want to surface review activity)
   - Link each PR by number with a short title.

5. **Open questions still pending**:
   - For each active feature in `<vault-root>/llmzone/work/10_projects/<feature>_<MonYY>/`, grep `## Open Questions` sections from the parent algorithm + decisions
   - List unresolved items with their feature + note context. Don't dump them all if there are many — pick the 3–5 most relevant to recent activity.

6. **Format output** per `--format`:

   - **bullets** (default): terse standup style
     ```
     **Recap (<since-date> → today)**

     **Vault**
     - <feature>: <new/updated note title> (status)
     - …

     **Code**
     - <repo>: <N commits>; key ones: <commit msgs>

     **PRs**
     - Merged: #<num> <title>
     - Open: #<num> <title>

     **Open questions**
     - <feature>: <question> ([[link]])
     ```

   - **slack**: 1–2 short paragraphs, conversational, with key wikilinks/PR links inline. Suitable for pasting into a #standup channel.

   - **email**: longer narrative with per-feature subsections. Suitable for a weekly update email — leads with what shipped, then what's in progress, then asks/blockers.

7. **If `--save` is set**: write the recap to `<vault-root>/llmzone/work/40_logs/sessions/<today>_recap-<window>.md` with frontmatter:
   ```yaml
   ---
   type: log
   scope: work
   date: <today>
   status: active
   tags: [llmzone, work, log, recap]
   ---
   ```
   Then run `python3 <vault-root>/llmzone/shared/scripts/vault.py rebuild` to refresh indices.

   If not `--save`: print only.

8. **Print**: the formatted recap to stdout, with the resolved window dates at top so the user sees what was covered.

## Notes

- Don't manufacture activity. If a section is empty (no PRs in window, no decisions written), say "(none this window)" rather than padding.
- Trim aggressively for the **slack** format — Slack messages > ~500 words get skimmed past. Lead with the most-shareable items (shipped PRs, decisions made), defer details to wikilinks.
- For multi-repo `code` activity, ask the user up-front which repos matter. Don't scan their entire `~/code/` tree unprompted — that's slow and surfaces noise.
- The recap is read-only on everything except the optional saved log file. Never mutate vault notes or code via this command.
- If `git log` returns commits not authored by the user (e.g., they've been merging others' PRs), bucket those separately under "merged from teammates" rather than mixing with own commits.
- For `--format email`, ask before sending — the command produces the draft, but the user copies it to their actual email client. Don't auto-send.
