---
description: Socratic dialogue to fill a decision record properly — alternatives, pros/cons, consequences
argument-hint: <kebab-topic> [<feature>]
---

You're invoking **vault decision**. The user wants to capture a non-trivial design choice. Walk them through the questions that produce a proper decision record (not just "we picked X"), then write it into the vault.

The vault root is from CLAUDE.md context; the LLM-managed area is `<vault-root>/llmzone/`. **Read `llmzone/shared/SKILL.md`** (especially the decision section requirements) and `llmzone/shared/templates/Decision_Record_Template.md` if you haven't this session.

## Steps

1. **Parse $ARGUMENTS**: first token = kebab-topic for the filename (e.g. `switch-from-foo-to-bar`); optional second = feature. Ask the user for whatever's missing.

2. **Run a Socratic dialogue** — use AskUserQuestion when there are clear option sets, plain text questions otherwise. Cover these in order, asking for follow-ups when answers are thin:

   - **What's being decided?** One sentence. (If the user gives a paragraph, paraphrase to one sentence and confirm.)
   - **What forced this decision?** Constraints, prior state, what breaks if we don't decide. The "Context" section.
   - **What alternatives did you consider?** Insist on at least 2. If they only have 1, ask "what's the do-nothing / status-quo option?" or "what's the obvious-but-rejected approach?"
   - **For each alternative, capture Pros and Cons** (3–5 bullets each). Push back if pros and cons feel one-sided — usually a real alternative has at least one genuine pro.
   - **What did you choose, and why?** Get the load-bearing reason — the one fact that tipped the decision. Distinguish "X is technically better" from "X is what the team will actually maintain."
   - **Consequences downstream?** What changes in code, conventions, or behavior. What becomes easier vs harder. Specific files/areas affected.
   - **Open questions still unresolved?** If any.
   - **Cross-refs**: which algorithms does this affect (`algorithms:` frontmatter)? Any PRs in flight that implement it (`prs:`)?

3. **Create the note**: `python3 <vault-root>/llmzone/shared/scripts/vault.py new decision <feature> <topic>`.

4. **Fill the body** from the dialogue answers:
   - TL;DR sentence (the one-sentence decision)
   - **Context** — from Q2
   - **Options considered** — H3 per option with summary + Pros + Cons from Q3/Q4
   - **Decision** — from Q5
   - **Consequences** — from Q6
   - **Open Questions** — from Q7 (omit section if none)
   - **Related** — populate frontmatter cross-refs from Q8; the AUTOGEN:related block fills in itself on rebuild

5. **Set `status:`**: `Proposed` if the decision is fresh and not yet implemented; `Accepted` if the user confirms it's signed off and being acted on.

6. **Run rebuild**: `vault rebuild`. Confirm no warnings.

7. **Print the note path** and a one-line summary of what was decided.

## Notes

- The dialogue is the value — don't shortcut to "just write the note from a quick description." The point is to surface the alternatives and tradeoffs that often go unexamined.
- For trivial decisions (the alternative is genuinely obvious), one alternative captured as "Considered: doing X, dismissed because Y" is acceptable per SKILL. Don't manufacture fake alternatives.
- If the user is impatient and skips through questions, ask one more time on the load-bearing ones (alternatives, load-bearing reason, consequences) — those are the hardest to reconstruct later from memory.
- Don't write the note while the dialogue is in progress — gather all answers first, then assemble. Lets the user revise earlier answers after seeing later questions.
