---
name: SKILL
description: Authoritative rules for placing, naming, and linking notes in llmzone. Read before any vault edit.
type: skill
scope: shared
zone: llmzone
status: active
tags: [llmzone, skill, llm, work, personal]
---

# SKILL

Use this guide before making any changes to `llmzone`.

## Goal

Keep the vault easy to search for both LLMs and humans by preserving:

- predictable structure,
- consistent metadata,
- canonical single-source notes,
- explicit evidence for claims,
- automatable indexing — top-level indices, per-feature `Archived.md`, per-note `Status` and `Related` blocks are all managed by `[[scripts/README|index_rebuild.py]]`. Do not hand-edit content between `<!-- AUTOGEN:* -->` markers.

## Tooling Policy

- Default to direct markdown file edits in the vault folders.
- Use `new_note.py` (see `[[scripts/README]]`) to create a new note from a template — it pre-fills frontmatter, paths, and date.
- For multi-file restructures, link updates, template changes, and frontmatter normalization, prefer direct markdown edits.
- After any structural change (creating, moving, archiving notes), run `python3 llmzone/shared/scripts/index_rebuild.py`. The script regenerates indices, derived statuses, and Related sections; it also warns when in-note `status:` disagrees with the derived state.

## Cleanup Cadence

- Run weekly cleanup using [[llmzone/shared/LLM_Cleanup_Playbook]] (10-15 min).
- Run monthly cleanup using [[llmzone/shared/LLM_Cleanup_Playbook]] (30 min).
- For each run, use [[llmzone/shared/templates/Cleanup_Run_Checklist_Template]].

## Required Workflow (Before Editing)

1. Open this file (`[[llmzone/shared/SKILL]]`) and confirm scope/path rules.
2. Determine `scope` first: `work`, `personal`, or `shared`.
3. Open the scope index:
   - work: `[[llmzone/work/00_index/Active_Work]]`
   - personal: `[[llmzone/personal/00_index/Active_Work]]`
4. Confirm target note type (see "Note types" below).
5. Run `[[llmzone/shared/Pre_Edit_Checklist]]`.
6. If creating a note, use `new_note.py` (or copy the corresponding template by hand).

## Placement Rules

- Work notes: `llmzone/work/**`
- Personal notes: `llmzone/personal/**`
- Shared templates/skills/scripts: `llmzone/shared/**`

### Feature-based layout (work scope)

Each unit of work is a **feature** living at the top of `10_projects/`. There is **no project layer** — features sit directly under `10_projects/`. The convention assumes most work belongs to the same underlying codebase project; if a feature happens to belong to a different project, it's just a sibling dir.

Feature directory: `<FeatureName>_<MonYY>` where `<MonYY>` is the month-year the feature work began (e.g. `Apr26`). Fixed for the life of the feature.

Inside each feature dir, exactly four note categories plus an autogen archive index:

```
10_projects/<FeatureName>_<MonYY>/
  algorithms/      one .md per algorithm; deep-dive steps go in a same-named subdir
  decisions/       one .md per decision (dated YYYY-MM-DD_<topic>.md)
  prs/             one .md per PR (dated YYYY-MM-DD_pr-<num>_<topic>.md)
  runbook/         build/test recipes; canonical: Build_and_Test_<FeatureName>.md
  Archived.md      autogen — script lists archived notes belonging to this feature
```

A new feature should grow these in roughly this order: algorithm → decision (capturing the why) → PR (per merge) → runbook (once there's a meaningful build/test loop).

Logs (`40_logs/daily/`, `40_logs/sessions/`) and archive (`50_archive/`) sit outside `10_projects/`.

## Note types

| Type | File location | Description |
|---|---|---|
| `algorithm` | `algorithms/<Name>.md` | Authoritative description of an algorithm pipeline. |
| `algorithm-step` | `algorithms/<Name>/Step<N>_<Name>.md` | Deep-dive on a single stage of a parent algorithm. |
| `decision` | `decisions/YYYY-MM-DD_<topic>.md` | Single ADR-style decision record. |
| `pr-summary` | `prs/YYYY-MM-DD_pr-<num>_<topic>.md` | One-per-PR summary of context, change, validation. |
| `runbook` | `runbook/Build_and_Test_<Feature>.md` (or `Reproduce_<topic>.md`) | Operational reference for building/testing the feature. |
| `log` | `40_logs/daily/YYYY-MM-DD.md` or `40_logs/sessions/YYYY-MM-DD_<topic>.md` | Time-ordered work log. |
| `index` | `00_index/*.md`, per-feature `Archived.md` | Index pages (mostly autogen). |
| `skill` | `shared/SKILL.md`, `shared/Pre_Edit_Checklist.md`, etc. | Authoritative rules / playbooks. |

## Filename conventions

| Type | Filename pattern |
|---|---|
| Feature dir | `PascalCase_<MonYY>` (e.g. `VolumeMesherSizeFunction_Apr26`) |
| Algorithm | `PascalCase.md` |
| Algorithm step | `Step<N>_PascalCase.md` (use digits, not letters, for sortability) |
| Decision | `YYYY-MM-DD_kebab-topic.md` |
| PR summary | `YYYY-MM-DD_pr-<num>_kebab-topic.md` |
| Runbook (canonical) | `Build_and_Test_<FeatureName>.md` |
| Runbook (ad-hoc) | `Reproduce_<kebab-topic>.md` |
| Daily log | `YYYY-MM-DD.md` |
| Session log | `YYYY-MM-DD_<kebab-topic>.md` |

## Frontmatter

Every note must include at least: `type`, `scope`, `date`, `status`, `tags`.

For project notes (under `10_projects/<feature>/` or `50_archive/<feature>/`), also: `feature`, `area` (optional, finer subsystem tag).

Type-specific extras:

| Type | Extra required | Optional |
|---|---|---|
| algorithm | — | `prs: []`, `decisions: []`, `supersedes: <Name>` |
| algorithm-step | `parent: <ParentAlgorithmName>` | — |
| decision | — | `superseded_by: <filename>`, `algorithms: []`, `prs: []` |
| pr-summary | `pr: <number>`, `branch:` | `algorithms: []`, `decisions: []`, `reverts: [<pr-num>]` |
| runbook | — | `algorithms: []` |

The cross-ref lists (`algorithms`, `decisions`, `prs`, etc.) drive the autogen Related sections and derived status — keep them set, the script does the rest.

## Status enums and lifecycle

| Type | Allowed values | Notes |
|---|---|---|
| algorithm / algorithm-step | `Proposed | Implemented | Deferred | Reverted | Superseded` | step usually mirrors parent |
| decision | `Proposed | Accepted | Deprecated | Superseded` | |
| pr-summary | `Proposed | Open | Merged | Reverted | Closed` | matches GitHub PR lifecycle |
| runbook | `Active | Outdated | Deprecated` | `Outdated` = commands stale; `Deprecated` = feature gone |
| log / index / skill | `active | archived` | |

### Who sets status

| Transition | Set by | Trigger |
|---|---|---|
| Proposed → Implemented (algorithm) | **auto** | a `prs:` entry has `status: Merged` |
| * → Superseded (algorithm/decision) | **auto** | another note's `supersedes:` / `superseded_by:` points here |
| * → Reverted (algorithm) | **auto** | most recent `prs:` entry is `Reverted` |
| Open → Merged (PR) | **human** | flip when GitHub merges (no `gh` integration in script) |
| Merged → Reverted (PR) | **human** | flip when GitHub revert merges; new PR's `reverts:` field handles propagation |
| * → Deferred | **human** | work is paused indefinitely |
| Proposed → Accepted (decision) | **human** | someone signs off |
| Active → Outdated (runbook) | **human** | you ran the commands and they failed |

The script writes a derived status badge into each note (between `<!-- AUTOGEN:status -->` markers) and surfaces derived state in the indices. Frontmatter `status:` is the human-curated baseline; the script does **not** overwrite it. Mismatches between baseline and derived produce a stderr warning.

## Tag taxonomy

Hybrid: small required base, free-form additions, script-managed reserved tags.

- **Required**: `[<feature-lowercase>, <type>]` (e.g. `[volumemeshersizefunction, algorithm]`). The script warns if either is missing.
- **Optional**: anything else — cross-cutting topics like `size-function`, `octree`, `testing`. Useful for `tag:#testing` searches across features.
- **Reserved**: `archived` is appended automatically when `status` flips to an archived state. Don't set it by hand.

## Section ordering and required content

Each note type has a corresponding template under `shared/templates/`. The template is the canonical section list and order — don't reshape sections without changing the template.

All notes follow these conventions:

- **TL;DR rule**: every note opens with a single sentence after the H1 stating the point. Both humans and LLMs should be able to answer "what is this" without scrolling.
- **Heading depth**: H1 once (= title, matches filename), H2 for major sections, H3 for subsections. H4 is acceptable but rare; needing H5+ usually means the note should split.
- **Open Questions**: each step file has a trailing `## Open Questions` for step-local questions; the parent algorithm note has a top-level `## Open Questions` for pipeline-wide ones. (Distinct from `## Coupling and known gaps`, which records facts about the current code.)
- **Related**: managed by the script between AUTOGEN markers. Hand-add extras (specific permalinks, related issues) outside the markers.

## Date semantics

| Type | What `date:` means |
|---|---|
| algorithm / algorithm-step | Date of last substantive update. Refresh when content materially changes. |
| decision | Date of the decision. Immutable after creation. |
| pr-summary | Date of PR creation/merge. Immutable. |
| runbook | Date last verified working — refresh whenever you re-run the commands and they pass. |
| log | Date of the work being logged. |

## Wikilink style

- **Sibling within same dir**: short form, `[[Step3_ZoneSeeding]]`.
- **Cross-algorithm-but-same-feature**: relative, `[[../VolumeMesherSizeFunction]]`.
- **Cross-feature or to indices**: full path, `[[llmzone/work/10_projects/.../Note]]`.
- For autogen blocks the script always uses full paths with `|Title` (so a renamed dir doesn't silently break the index).

## Content Rules

- Authoritative discussions live in vault notes (`llmzone/**`).
- Codebase docs are implementation references, not the primary discussion.
- If a code doc has deeper details than the vault note, copy/sync those into the vault note.
- Prefer links over duplication.
- When citing code, use GitHub permalinks pinned to a commit SHA, not bare `file.cpp:NNN` references — line numbers drift. The helper script at [[scripts/README|permalink_rewrite.py]] converts existing references idempotently.

## Markdown formatting

- Do not hard-wrap sentences. One sentence (or list item, or paragraph) is one line, regardless of length. Obsidian soft-wraps for display; hard wrapping makes diffs noisy and breaks long inline links.
- Never insert a line break inside a backticked code span (`` `...` ``) or inside a markdown link's `[text](url)`. Both render incorrectly.
- Blank lines still separate paragraphs and list items as usual.
- Include exact command evidence for validation claims.

## Archiving

- Move the note from `10_projects/<feature>/<subdir>/<note>.md` to `50_archive/<feature>/<subdir>/<note>.md`, set `status:` to the archived equivalent.
- **Do not leave a pointer stub** at the old path. The per-feature `Archived.md` and the MoC archive section provide discovery.
- Run `index_rebuild.py` to refresh.
- If an entire feature is fully archived (no remaining active notes), the feature dir under `10_projects/` may be removed; `50_archive/<feature>/` and the MoC's archive section continue to surface it.

## Anti-Patterns

- Do not mix multiple intents in one note.
- Do not keep duplicate canonical summaries in multiple places.
- Do not paste large transcripts as primary content.
- Do not leave active notes without frontmatter.
- Do not write a `scope: work` note under `personal/` (or vice versa).
- Do not leave a pointer stub at the old path when archiving.
- Do not place a note under a `10_projects/<project>/<subdir>/` layout — the project layer is removed.
- Do not hand-edit content between `<!-- AUTOGEN:* -->` markers — rerun the script instead.
- Do not hard-wrap sentences mid-line.

## Quick Checklist

- [ ] Scope selected first
- [ ] Path matches the feature-based layout
- [ ] Filename matches the convention for this note type
- [ ] `feature` frontmatter set (for project notes)
- [ ] `type` correct; cross-ref lists (`algorithms`, `decisions`, `prs`) populated
- [ ] Required tags `[<feature-lowercase>, <type>]` present
- [ ] TL;DR sentence present after H1
- [ ] `index_rebuild.py` run after structural changes
- [ ] Validation evidence present (if technical claim)
