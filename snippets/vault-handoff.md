---
description: Generate a one-page handoff doc for a colleague joining a feature
argument-hint: <FeatureName>
---

You're invoking **vault handoff**. The user wants a single-page summary of a feature's state suitable for sharing with a colleague who's joining the work — current status, key concepts, open questions, how to build/test, recent activity, suggested next steps.

The vault root is from CLAUDE.md context; the LLM-managed area is `<vault-root>/llmzone/`. **Read `llmzone/shared/SKILL.md`** if you haven't this session.

## Steps

1. **Resolve the feature**: $ARGUMENTS is the feature name (without `_<MonYY>`). Find the dir under `<vault-root>/llmzone/work/10_projects/` matching `<FeatureName>_*`. If multiple match or none match, ask the user.

2. **Read the feature's notes**:
   - All algorithm parents in `algorithms/` (skip step children — they're for deep-divers)
   - All decisions in `decisions/`
   - All PR summaries in `prs/`
   - The runbook in `runbook/`
   - `Archived.md` for retired items
   - `vault-root/llmzone/work/40_logs/sessions/*.md` files that mention this feature in tags or body (last 3–5)

3. **Pull current state** from each:
   - Status badges (AUTOGEN:status block)
   - Open Questions sections
   - Last-touched dates
   - Cross-ref lists (which decisions, which PRs, which algorithms link together)

4. **Generate the handoff doc** in this structure:

   ```
   # Handoff: <FeatureName> (<Month YYYY>)

   ## What this feature is
   2–4 sentences: the problem, the approach, why it matters.

   ## Current state
   - **Implemented**: <list algorithms/PRs that are landed>
   - **In progress**: <list Proposed/Open ones>
   - **Deferred / blocked**: <list Deferred and why>

   ## Key concepts
   3–6 bullets pulling from the algorithms' TL;DRs, with wikilinks.

   ## Decisions you should know
   - [[<decision>]] — one-line rationale
   - (repeat)

   ## How to build & test
   Pull the canonical commands from the runbook verbatim, with the runbook wikilink.

   ## Open questions
   Aggregate Open Questions from active algorithms + decisions. Cite each note.

   ## Recent activity
   Last 3–5 PRs (with status), last 1–2 session logs (with date).

   ## Suggested next steps for someone picking this up
   2–4 bullets — what looks unblocked, what depends on what.

   ## All notes
   Full list of feature's active notes as wikilinks, grouped by type.
   ```

5. **Print it inline** by default. Ask the user if they want it saved as a session log (`vault new` doesn't have a "handoff" type — would just be a regular log under `40_logs/sessions/YYYY-MM-DD_handoff-<feature>.md`). If yes, write the file directly with appropriate frontmatter (`type: log`, `tags: [..., handoff, <feature-lowercase>]`) and run `vault rebuild`.

## Notes

- Don't dump full note bodies — summarize and link. The handoff is a navigation aid, not a replacement for reading the notes.
- Be honest about gaps. If a runbook is `Outdated` or open questions are unresolved, say so plainly — the incoming person needs to know.
- Length target: ~1 printed page. Trim aggressively if you exceed it; add more "see [[X]]" links rather than more inline content.
