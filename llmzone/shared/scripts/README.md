---
type: index
scope: shared
zone: llmzone
status: active
tags: [llmzone, scripts, tools]
---

# Shared scripts

Reusable utilities for maintaining vault notes.

## vault.py (unified CLI)

Single entry point that wraps the other scripts and adds higher-level commands. Every mutating subcommand auto-runs `index_rebuild.py` after, so indices, status badges, and Related sections stay fresh without a manual second step.

### Usage

```sh
# Create a new feature dir scaffolding (algorithms/, decisions/, prs/, runbook/)
python3 vault.py new feature <PascalName> [--month Apr26]

# Create notes (delegates to new_note.py)
python3 vault.py new algorithm <feature> <Name>
python3 vault.py new algorithm-step <feature> <ParentName> <Step1_Name>
python3 vault.py new decision <feature> <kebab-topic>
python3 vault.py new pr <feature> <pr-number> <kebab-topic> [--branch X]
python3 vault.py new runbook <feature> [<Name>]

# Move an active note to 50_archive/ with a terminal status (defaulted by type:
# algorithm→Superseded, decision/runbook→Deprecated, log→archived).
python3 vault.py archive <note-stem> [--status <terminal>]

# Refresh indices manually (same as index_rebuild.py).
# --gh-sync fetches each PR note's status from GitHub and updates frontmatter.
python3 vault.py rebuild [--dry-run] [--gh-sync]

# List GitHub PRs that don't have a corresponding vault note.
python3 vault.py prs [--repo OWNER/REPO] [--state all|open|closed|merged] [--author @me]

# Health check — dangling wikilinks, missing TL;DR, missing feature frontmatter,
# stale runbooks, GitHub PR drift (via gh-sync dry-run), index drift.
python3 vault.py check [--no-gh] [--no-stale] [--stale-days N]
```

### `vault check` details

The check exits 0 only if all of these pass:

- **Dangling wikilinks**: every `[[target]]` in note bodies (excluding AUTOGEN blocks) resolves to a real file. Resolution: full vault-relative paths first, then relative-to-source, then by stem across the vault.
- **Missing TL;DR**: required for `algorithm`, `decision`, `pr-summary`, and `runbook` notes. The first non-blank, non-AUTOGEN, non-quote line after the H1 must look like a sentence (≥4 words, not a heading). `algorithm-step` notes are exempt — their template doesn't include one.
- **Missing `feature:` frontmatter**: required on every note under `10_projects/` of type algorithm/algorithm-step/decision/pr-summary/runbook.
- **Stale runbooks** (skip with `--no-stale`): runbook `date:` older than `--stale-days` (default 60). Suggests the build/test recipe should be re-verified.
- **GitHub PR drift** (skip with `--no-gh`): runs `index_rebuild.py --gh-sync --dry-run` to flag PR notes whose in-note status disagrees with GitHub's.
- **Index drift**: runs `index_rebuild.py --dry-run` to detect any stale autogen sections (Active_Work, MoC, per-feature Archived.md, per-note Status/Related blocks).

### GitHub integration

Three behaviors require `gh` (the GitHub CLI) to be installed and authenticated:

- `vault new pr <feature> <num>` — auto-fills title (→ kebab topic), branch, URL, and initial status from `gh pr view <num>`. Pass `--no-gh` or `--branch <name> <topic>` to opt out.
- `vault rebuild --gh-sync` (or `index_rebuild.py --gh-sync`) — for every PR note, fetches GitHub state and overwrites the in-note `status:` and `branch:` fields. Authoritative for those fields; manual edits get overwritten on next sync.
- `vault prs` — lists `gh pr list --author @me --state all` cross-referenced against existing PR notes; prints only the PRs that don't yet have a note.

Repo discovery: by default the script extracts `owner/repo` from the `https://github.com/<owner>/<repo>/pull/<num>` URL embedded in each PR note's body. Falls back to `_gh.py`'s `DEFAULT_REPO` (set via `setup.sh`) if no URL is present. If `DEFAULT_REPO` is empty too, gh is invoked without `--repo` and falls back to its own auto-detection from the cwd's git remote — which only works if you run the scripts from inside a checkout of your code repo.

### Suggested shell alias

```sh
alias vault='python3 ~/obsidian/myvault/llmzone/shared/scripts/vault.py'
```

Then: `vault new decision VolumeMesherSizeFunction my-topic` etc.

## new_note.py

Creates a new vault note from its template, pre-filling frontmatter (date, feature, paths, names) so you don't have to find-and-replace placeholders by hand.

### Usage

```sh
python3 new_note.py algorithm <feature> <AlgorithmName>
python3 new_note.py algorithm-step <feature> <ParentAlgorithmName> <Step1_Name>
python3 new_note.py decision <feature> <kebab-topic>
python3 new_note.py pr <feature> <pr-number> <kebab-topic> [--branch <name>]
python3 new_note.py runbook <feature> [<RunbookName>]      # default: Build_and_Test_<feature>
```

The feature dir (`work/10_projects/<feature>_<MonYY>/`) must already exist. Run `index_rebuild.py` after creating the note to refresh indices and Related sections.

## index_rebuild.py

Rebuilds the auto-generated sections of `work/00_index/Active_Work.md`, `work/00_index/Map_of_Contents.md`, and per-feature `work/10_projects/<Feature>_<MonYY>/Archived.md`. Walks active feature dirs and `50_archive/`, reads `feature:` frontmatter, and rewrites content between `<!-- AUTOGEN:<name> START/END -->` markers. Hand-written content above/below markers is preserved.

### Why this exists

Hand-maintaining `Active_Work` and the MoC's Projects/Archive sections is error-prone — links rot, sections get out of sync with what's actually on disk, and adding a new feature means touching three files. This script regenerates those sections from the on-disk state and frontmatter, so the only required step after creating/moving/archiving a note is a one-line invocation.

### Usage

```sh
python3 ~/obsidian/myvault/llmzone/shared/scripts/index_rebuild.py [--dry-run]
```

Idempotent. Safe to run repeatedly. Run after any structural change (new feature dir, moved note, archive move, status flip).

### Requirements

- Each active feature dir must be named `<FeatureName>_<MonYY>` (e.g. `VolumeMesherSizeFunction_Apr26`).
- Every project note (active or archived) must have `feature: <FeatureName>` in frontmatter — this is what the script uses to group notes.
- Subdirs under each feature: `algorithms/`, `decisions/`, `prs/`, `runbook/`. Top-level `*.md` per subdir is what gets listed; nested files (e.g. `algorithms/<Algo>/Step*.md`) are reached via the parent's deep-dive links and are intentionally not surfaced in the index.

## permalink_rewrite.py

Converts backtick-wrapped `file.cpp:NNN` references in markdown files into GitHub permalinks pinned at a given commit SHA. Visible link text stays identical to the original backtick string, so notes stay readable when GitHub is unreachable. Idempotent — already-linked references are skipped.

### Why this exists

Bare `VolumeMesher.cpp:489` style references rot fast as code drifts. A permalink to a specific SHA freezes the citation at the commit the note describes. See [[../SKILL]] for vault-wide conventions.

### Usage

The basename → repo-relative-path map is auto-derived from `git ls-files` in `--repo-root`, so it never goes stale as files are moved or renamed. References that already include a path prefix (e.g. `src/.../VolumeMesher.cpp:489`) bypass the map and link directly.

```sh
cd /path/to/repo && SHA=$(git rev-parse origin/master)
python permalink_rewrite.py \
    --sha "$SHA" \
    --repo <owner>/<repo> \
    --repo-root /path/to/repo \
    --dry-run \
    /path/to/note1.md /path/to/note2.md
```

Drop `--dry-run` to apply.

### Ambiguous basenames

If two files in the repo share a basename (e.g. multiple `Utils.cpp` in different directories), the auto-derived map drops the basename. References to it in notes won't resolve. Two ways out:

- Use the full path in the note: write `` `src/foo/Utils.cpp:42` `` instead of `` `Utils.cpp:42` ``.
- Pass `--paths-json override.json` with explicit `{"Utils.cpp": "src/foo/Utils.cpp"}` entries; these take precedence over the auto-derived map.

### Re-pinning when code moves

The script is idempotent on the *same* SHA but does not detect already-permalinked references that point at an *older* SHA. To re-pin a note to a newer SHA:

```sh
sed -i 's|github.com/<owner>/<repo>/blob/<old-sha>|github.com/<owner>/<repo>/blob/<new-sha>|g' note.md
```

Then run `permalink_rewrite.py` again to catch any new references that weren't already linked. Run `verify_permalinks.py` afterwards to confirm the new SHA still has all the linked paths.

### Supported file types

The regex matches `.cpp`, `.h`, `.cu`, `.cuh`, `.py`, `.ts`, `.tsx`, `.js`, `.rs`, `.go` — extend `PATTERN` and `INDEXED_EXTENSIONS` in the script for other extensions.

## verify_permalinks.py

Coarse-grained staleness check for GitHub permalinks already embedded in vault notes. Walks one or more markdown files (or directories), parses each `github.com/.../blob/<sha>/<path>#L<a>[-L<b>]` link, and reports four failure modes against a local clone:

- **PATH-MOVED-OR-DELETED** — the linked path no longer exists at master.
- **LINES-OUT-OF-RANGE** — the path exists at master but the line range now falls outside the file's current length.
- **SYMBOL-MISSING** — the closest backticked identifier on the link's line no longer appears anywhere in the file at master.
- **SYMBOL-DRIFTED** — the identifier is in the file but outside the linked line range (line numbers have shifted).

The symbol checks are heuristic. The script picks the closest backticked identifier on the same line as the link as the candidate "subject" and looks for it in the linked file. Two failure modes for the heuristic:

- **Wrong symbol picked.** If the line has multiple backticked names, the script picks the nearest by distance, which isn't always the link's true subject. Result: SYMBOL-MISSING or SYMBOL-DRIFTED reports for an irrelevant symbol.
- **Class-inline methods.** A C++ method defined inside a struct body usually only appears as `Class::method` at call sites, not at the definition. The script tries the qualified form first, then falls back to the bare last component (`method`), which catches most cases but can over-match if the bare name is generic.

These don't flag *real* failures — just produce some flags that need human review to dismiss. Symbol checks can be turned off entirely with `--no-symbol-check` if the noise outweighs the signal for your project.

The script does NOT try to track functions across file moves (would need `git log -L:<symbol>:<file>` integration; not built).

### Usage

```sh
python verify_permalinks.py \
    --repo <owner>/<repo> \
    --repo-root /path/to/your/repo \
    --ref main \
    ~/obsidian/myvault/llmzone/work/10_projects/MyFeature_Apr26/
```

Directory arguments are walked recursively for `.md` files. Exit code is 0 when all permalinks are clean, 1 otherwise. Add `--no-symbol-check` to limit the report to PATH and LINES failure modes.

### Recommended cadence

Run every few weeks, or whenever you're about to substantively edit a note that has lots of permalinks. Walk the whole `llmzone/work/10_projects/<Feature>_<MonYY>/` directory at once so a single pass surfaces everything. For each flagged citation, either re-pin the link to a newer SHA where the citation is still accurate, or rewrite the surrounding text to match the new code state.

## reflow.py

Unwraps soft-wrapped markdown so each paragraph and each list item is one physical line. Per the vault's formatting rule (see [[../SKILL]]): lines from "start to full stop" should not contain linebreaks; Obsidian soft-wraps for display.

Preserved verbatim: YAML frontmatter, fenced code blocks (including ``` mermaid), ATX headings, horizontal rules, tables, blank lines.

Idempotent.

### Usage

```sh
python reflow.py [--dry-run] <markdown-file> [<markdown-file>...]
```

### Limitations

- Doesn't sentence-split: a multi-sentence paragraph stays on one line. The vault rule only forbids linebreaks *within* a sentence, so this is correct, but if you want stricter "one sentence per line" output, post-process manually.
- Loose lists with blank-line-separated continuation paragraphs inside a single item aren't handled — the continuation will be re-attached as a separate paragraph. Avoid those, or fix manually.
