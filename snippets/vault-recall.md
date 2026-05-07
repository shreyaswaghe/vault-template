---
description: Search the vault for what's already documented about a topic before starting new work
argument-hint: <topic-keywords>
---

You're invoking **vault recall**. The user wants to know what's already documented about a topic before starting new work — to avoid redocumenting and to surface relevant prior context.

The vault root is from CLAUDE.md context; the LLM-managed area is `<vault-root>/llmzone/`. **Read `llmzone/shared/SKILL.md`** if you haven't this session.

## Steps

1. **Capture the query**: $ARGUMENTS is the topic. Treat it as a phrase first; if it has multiple words, also consider each word as a separate term.

2. **Grep across vault**:
   - `grep -rli "<topic>" llmzone/work/ llmzone/work/50_archive/` (case-insensitive, file-listing)
   - For multi-word queries, also try each significant word individually
   - Skip `__pycache__/` and the autogen index files (those would just echo other notes)

3. **Rank hits** by likely relevance:
   - Active feature notes (in `10_projects/`) outrank archived ones
   - Algorithm and decision notes outrank PR summaries (more authoritative)
   - Notes whose H1 or TL;DR match the topic outrank notes that just mention it once in the body

4. **Read the top 3–5 hits** in full (or top 8 quickly if everything is short). For each, capture:
   - The note's H1 + TL;DR sentence
   - Status (from frontmatter or AUTOGEN:status badge)
   - Cross-refs (`algorithms:`, `decisions:`, `prs:`, `supersedes:`)
   - Any specific sections that directly speak to the topic

5. **Look at the cross-refs** of matching notes — pull in 1–2 hops of related notes if they look germane.

6. **Output** as a structured response:
   - **What's documented**: bulleted list of relevant notes with wikilinks, each annotated with one-line TL;DR and status
   - **Key takeaways**: 2–4 bullets summarizing what the vault says about the topic, citing the notes
   - **Adjacent context**: notes that came up via cross-ref but aren't direct hits (worth knowing about)
   - **Gaps**: aspects of the topic the vault doesn't cover, that the user might want to write up if they're about to work on it

## Notes

- Read-only — don't write to the vault.
- Don't quote large chunks of notes; cite wikilinks and let the user open them.
- If grep returns nothing, say so plainly and check whether the topic might be archived (search `50_archive/` more carefully). If still nothing, suggest `vault new feature` or `vault new algorithm` as the natural starting point.
- If the query is too generic ("octree", "config"), narrow with the user — too many hits is its own failure mode.
