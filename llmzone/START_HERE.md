---
type: index
zone: llmzone
status: active
tags: [llmzone, start]
---

# START_HERE

This is the entry point for the LLM-managed area of an Obsidian vault using the [vault-template](https://github.com/) layout. Both humans and LLMs should read this before navigating or editing.

## What lives here

The vault has three scopes under `llmzone/`:

- **`work/`** — engineering work notes (default for code-project topics)
- **`personal/`** — personal notes
- **`shared/`** — templates, conventions, helper scripts (vault-wide tooling)

## Quick navigation

| To find... | Read |
|---|---|
| Currently active features and notes | [[llmzone/work/00_index/Active_Work]] |
| Full map of work-scope content | [[llmzone/work/00_index/Map_of_Contents]] |
| The rules for editing the vault | [[llmzone/shared/SKILL]] |
| The scripts that maintain it | [[llmzone/shared/scripts/README]] |
| Personal-scope index | [[llmzone/personal/00_index/Active_Work]] |

## How `work/` is organized

`work/10_projects/` is **feature-based**. There is no per-project layer — each unit of work is a top-level dir named `<FeatureName>_<MonYY>` (the month-year the feature work began, fixed for the life of the feature).

Inside each feature dir, exactly four content subdirs plus an autogen archive index:

```
work/10_projects/<FeatureName>_<MonYY>/
  algorithms/      one .md per algorithm; deep-dive steps in same-named subdir
  decisions/       YYYY-MM-DD_<topic>.md, one per decision
  prs/             YYYY-MM-DD_pr-<num>_<topic>.md, one per PR
  runbook/         build/test recipes; canonical: Build_and_Test_<Feature>.md
  Archived.md      autogen — script lists archived notes for this feature
```

Other top-level dirs:

- `work/00_index/` — `Active_Work.md`, `Map_of_Contents.md`, `Tags_and_Conventions.md` (autogen sections inside)
- `work/20_domains/`, `work/30_patterns/` — cross-project knowledge
- `work/40_logs/{daily,sessions}/` — time-ordered logs
- `work/50_archive/` — archived/superseded notes (no pointer stubs left at old paths)

## Note types

Five canonical types in `work/`:

| Type | Where | Purpose |
|---|---|---|
| `algorithm` | `algorithms/<Name>.md` | Authoritative description of an algorithm pipeline |
| `algorithm-step` | `algorithms/<Name>/Step<N>_<Name>.md` | Deep-dive on one stage of a parent algorithm |
| `decision` | `decisions/YYYY-MM-DD_<topic>.md` | ADR-style decision record |
| `pr-summary` | `prs/YYYY-MM-DD_pr-<num>_<topic>.md` | One-per-PR summary |
| `runbook` | `runbook/Build_and_Test_<Feature>.md` | Operational reference |

Plus `log` (in `40_logs/`), `index` (autogen index pages), and `skill` (under `shared/`).

## How to add a note

1. **Identify the feature dir** (or create one as `<FeatureName>_<MonYY>/`).
2. **Use the helper**: `python3 llmzone/shared/scripts/new_note.py <type> <feature> <name>` — it picks the template, fills frontmatter, sets the date, and writes to the canonical path.
3. **Edit the body** to fill in content.
4. **Run `index_rebuild.py`** (see Automation below) to refresh indices and Related sections.

## Conventions

Detailed rules live in [[llmzone/shared/SKILL]]. Key ones:

- **Filename, frontmatter, status enums, cross-ref fields per type** are spelled out in SKILL.
- **TL;DR rule**: every note opens with one sentence after the H1 stating the point.
- **Markdown line wrapping**: do not hard-wrap sentences. One sentence, list item, or paragraph is one line, however long. Never break a backticked span or a markdown link.
- **Code citations**: use GitHub permalinks pinned to a commit SHA, not bare `file.cpp:NNN`. The helper at `[[llmzone/shared/scripts/README|permalink_rewrite.py]]` converts existing references.
- **Headings**: H1 once (= title), H2 for major sections, H3 for subsections. Past H4 means the note should split.

## Automation

Three scripts under `llmzone/shared/scripts/`:

- **`new_note.py`** — create a note from its template with placeholders filled.
- **`index_rebuild.py`** — refresh `Active_Work`, MoC, per-feature `Archived.md`, plus per-note `Status` badge and `Related` section. Run after any structural change. Idempotent.
- **`permalink_rewrite.py`** — convert backticked `file.cpp:NN` to SHA-pinned GitHub permalinks. Idempotent.
- **`verify_permalinks.py`** — staleness check for already-permalinked references against the current code.

`index_rebuild.py` writes between `<!-- AUTOGEN:* -->` markers — never hand-edit that content; rerun the script.

## For LLMs (mandatory before editing the vault)

1. **Read [[llmzone/shared/SKILL]] in full** before any vault edit. It is the authoritative rule set.
2. **Use `new_note.py`** rather than hand-creating files from templates.
3. **After any structural change**, run `python3 llmzone/shared/scripts/index_rebuild.py`.
4. **Never edit between `<!-- AUTOGEN:* -->` markers** — the script will overwrite your edits and you'll lose the work.
5. **Persist work that future sessions will need**: PR summaries, decision records, algorithm notes, session logs — write them into the vault rather than leaving them in conversation context.
