# vault-template

A reference Obsidian vault skeleton for engineering teams who use Claude Code (or any LLM coding assistant) to maintain knowledge alongside the code they're writing. The conventions, scripts, and Claude Code integration are extracted from a working personal vault.

## What you get

- **Predictable per-feature structure** under `llmzone/work/10_projects/<FeatureName>_<MonYY>/{algorithms,decisions,prs,runbook}/`.
- **Five canonical note types** — `algorithm`, `algorithm-step`, `decision`, `pr-summary`, `runbook` — each with a templated section list and required frontmatter.
- **Auto-generated indices**: `Active_Work.md`, `Map_of_Contents.md`, per-feature `Archived.md`, plus per-note **Status badge** and **Related** sections derived from cross-reference frontmatter.
- **GitHub integration**: PR notes auto-fill from `gh pr view`; statuses sync from GitHub state on demand; `vault prs` lists PRs missing a note.
- **Health check**: `vault check` finds dangling wikilinks, missing TL;DRs, missing frontmatter, stale runbooks, GitHub drift, and index drift.
- **Claude Code integration**: a SessionEnd hook keeps indices fresh, a `/vault-checkin` slash command summarizes and persists session-worthy work.

The authoritative rules live in [`llmzone/shared/SKILL.md`](llmzone/shared/SKILL.md). Read that first.

## Setup

### 1. Clone into your Obsidian vault directory

```sh
# Pick a vault location (must not already contain an Obsidian vault)
git clone <this-repo-url> ~/obsidian/myvault
cd ~/obsidian/myvault
```

Open `~/obsidian/myvault` in Obsidian. The `llmzone/` folder is the LLM-managed area; you can add personal notes elsewhere.

### 2. Run the setup script

```sh
./setup.sh
```

Interactive. Asks for your default GitHub repo, optionally installs the `/vault-checkin` slash command, runs a smoke test, and prints the snippets you need to manually paste into `~/.claude/CLAUDE.md` and `~/.claude/settings.json`. Safe to re-run.

The two things `setup.sh` deliberately does **not** do automatically (because they touch shared user config):

- **Append to `~/.claude/CLAUDE.md`** — the script prints the personalized snippet; you paste it manually so it doesn't conflict with your existing context.
- **Merge into `~/.claude/settings.json`** — same reason. The hook should be added under the existing `hooks` key (don't replace the whole file).

### 3. Suggested shell alias

```sh
alias vault='python3 ~/obsidian/myvault/llmzone/shared/scripts/vault.py'
```

Then `vault check`, `vault new feature MyFeature`, `vault new pr MyFeature 1234`, etc.

### 4. Verify

```sh
vault check
```

Should report all checks clean (no features yet, but no errors).

## Day-to-day usage

```sh
# Create a feature dir scaffolding (algorithms/, decisions/, prs/, runbook/)
vault new feature VolumeMesherSizeFunction

# Add notes
vault new algorithm VolumeMesherSizeFunction MyAlgo
vault new decision VolumeMesherSizeFunction switch-from-foo-to-bar
vault new pr VolumeMesherSizeFunction 4721           # auto-fills from gh
vault new runbook VolumeMesherSizeFunction

# Move a finished note to the archive (sets terminal status, no pointer stubs)
vault archive MyAlgo

# Sync PR statuses from GitHub
vault rebuild --gh-sync

# Find PRs that don't have a vault note
vault prs

# Health check
vault check
```

## Customization

Defaults that may not match your environment:

- **Default GitHub repo** is empty out of the box; `setup.sh` prompts for it and writes the value into `llmzone/shared/scripts/_gh.py` as `DEFAULT_REPO`. With it set, `vault new pr <feature> <num>` and `vault prs` work without a `--repo` flag. With it empty, you must pass `--repo OWNER/REPO` per call (or run from inside a checkout of your code repo so `gh` auto-detects).
- **Stale-runbook threshold** is 60 days. Override with `vault check --stale-days 30`.
- **Note types and section templates** are in `llmzone/shared/templates/`. Edit if you want different sections; just keep the AUTOGEN markers.

The conventions are deliberately opinionated — the value comes from convergence within a team, not flexibility. Resist customizing the structure unless you have a real reason.

## Requirements

- Python 3.10+
- `gh` CLI (for GitHub integration; not required for the rest)
- An Obsidian app (for the vault UX; the scripts work without it)
- A markdown editor that handles wikilinks (Obsidian, Logseq, or just any editor — wikilinks render as plain text elsewhere)

## When things break

- `vault check` is the first stop. It surfaces most class of issue (missing frontmatter, broken links, stale notes).
- If `index_rebuild.py` clobbers a note unexpectedly, your vault is git-tracked — `git diff` and `git restore` will save you.
- `LLM_Cleanup_Playbook.md` documents weekly + monthly maintenance routines.

## Updates

This repo holds shared infrastructure (scripts, templates, SKILL/playbook docs). When the upstream improves them, you can `git pull` to get the new versions. Your own notes under `llmzone/work/` and `llmzone/personal/` are unaffected unless you've edited the shared files yourself.

If you fork and customize the scripts heavily, future merges will be painful — consider tracking shared infra in a git submodule instead.
