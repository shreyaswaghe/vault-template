---
description: Walk a code function/file and draft an algorithm note skeleton with permalinks pre-pinned
argument-hint: <code-ref> [<feature>] [<AlgorithmName>]
---

You're invoking **vault algo**. The user wants you to read code and produce a draft `algorithm` note for the vault with the standard sections filled and permalinks pinned to the current commit SHA.

The vault root is from CLAUDE.md context; the LLM-managed area is `<vault-root>/llmzone/`. **Read `llmzone/shared/SKILL.md`** (especially the algorithm section requirements) and `llmzone/shared/templates/Algorithm_Template.md` if you haven't this session.

## Steps

1. **Parse $ARGUMENTS**: first token = code reference (file path, `file:line`, or function name); optional second = feature name; optional third = algorithm name (PascalCase). Ask the user for missing pieces before proceeding.

2. **Locate the code**:
   - If a path: read the file. If `file:line`, jump to that section. If a function name: grep across the relevant code repo to find the definition.
   - Read enough surrounding code to understand inputs, outputs, and called helpers (typically the function body + 1 hop into key helpers).

3. **Pin to a SHA**: in the code repo, run `git rev-parse HEAD` (or `git rev-parse origin/main`). Note this SHA — you'll embed it in permalinks.

4. **Identify the pipeline structure**:
   - Sequential stages (top-level operations the function performs in order)
   - Inputs (parameters, configs read, upstream state assumed)
   - Outputs (return values, mutations, downstream consumers)
   - Configs / magic numbers
   - Coupling / known gaps (implicit dependencies, dead branches, undocumented invariants)

5. **Decide name + feature** if not given:
   - Name: PascalCase derived from the function/class (e.g. `GAIBasedSizeFunction` → `GAIBasedSizeFunction`)
   - Feature: ask the user; suggest based on path heuristics (which feature dir is most relevant)

6. **Create the note**: `python3 <vault-root>/llmzone/shared/scripts/vault.py new algorithm <feature> <Name>`.

7. **Fill the body**:
   - **TL;DR**: one sentence stating what problem this algorithm solves
   - **Implementation refs**: bulleted file paths (no line numbers at this level)
   - **Pipeline**: a Mermaid `flowchart TD` for multi-stage pipelines (skip if 1–2 stages)
   - **Inputs and outputs**: types and meanings
   - **Stages**: H3 per stage with one-line summary, deep-dive link placeholder (`[[<Name>/Step<N>_...]]` in backticks if step doesn't exist yet), and the configs each stage touches with permalinks to the relevant lines
   - **Querying / Usage**: how callers invoke this, big-O cost
   - **Coupling and known gaps**: be specific — magic numbers (with values), implicit dependencies, dead branches you noticed
   - **Complexity summary**: only if you can derive it confidently from the code
   - **Open Questions**: things unclear from code reading that the user should answer

8. **Convert all `file.cpp:NN` references to permalinks** using the SHA from step 3. Either invoke `permalink_rewrite.py`:
   ```
   python3 <vault-root>/llmzone/shared/scripts/permalink_rewrite.py \
       --sha <SHA> --repo <owner>/<repo> --repo-root <repo-path> \
       <new-note-path>
   ```
   or write the permalinks inline as you author. Format: `[`file.cpp:NN`](https://github.com/<owner>/<repo>/blob/<sha>/<path>#LNN)`.

9. **Run rebuild**: `vault rebuild`. Confirm no warnings.

10. **Print summary**: note path, SHA pinned to, what sections still need user input (e.g. "I left Complexity summary blank because the code's costs aren't obvious from inspection — fill in based on what you know about typical workloads").

## Notes

- Don't fabricate behavior the code doesn't show. If a stage is opaque, say so in **Coupling and known gaps** rather than guessing.
- For step deep-dives (`Step1_X.md`, `Step2_Y.md`): only create them if the user asks. The parent algorithm note alone is usually enough for first-pass; steps come later when a stage merits its own page.
- If the algorithm is the only one for its feature, the runbook can be created next via `vault new runbook <feature>`.
