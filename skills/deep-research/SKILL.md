---
name: deep-research
description: Use when the user wants thorough multi-source research synthesized into a cited report — "research X", "go deep on Y", compare A vs B vs C, survey/landscape the state of Z, literature reviews, or technical deep-dives that need many sources reconciled. Not for single-fact lookups answerable in one search.
---

# Deep Research

## Overview

Produce a **citation-verified research report** by scoping the question, fanning out
parallel research sub-agents proportional to complexity, verifying every citation
against its source, then synthesizing. Core principle: **spend effort proportional
to the question, ground every claim in a primary source you actually opened, and
never present an unverified citation as fact.**

## When to use

- "Research X", "go deep on Y", "compare A vs B vs C", "survey the state of Z",
  landscape/market scans, literature reviews, technical deep-dives needing many sources.
- **Skip** for a single fact — one `WebSearch` answers it; just answer directly.

## The loop: Scope → Gauge → Research → Verify → Write

### 1. Scope
Ask at most **3 clarifying questions** that most reduce ambiguity (intent, depth,
boundaries). If the user said "just go" / "you decide", or the request is already
specific, skip asking. Then write a one-line **objective** and 2–6 **independent
sub-questions** that can be researched in parallel. The objective is your north star —
restate it inside every sub-agent prompt.

### 2. Gauge complexity (the cost gate)
Don't over-spawn. Match effort to the question:

| Tier | Looks like | Sub-agents |
|---|---|---|
| Simple | one fact / definition | 0 — answer directly with 1–2 searches |
| Standard | focused, a few angles | 2–3 parallel |
| Deep | broad / comparative / open-ended | 4–6 parallel |

If a request matches **two tiers** (e.g. a comparison that's also open-ended), pick
the **higher** tier unless the user constrained the scope.

### 3. Research — dispatch parallel sub-agents
Launch one `Task` sub-agent per sub-question **in a single message** so they run
concurrently. (**If sub-agents are unavailable, do each sub-question yourself,
sequentially, under the same contract.**) Give each agent explicitly:
- **Objective + its one sub-question**, and how it serves the overall objective.
- **Source guidance** — start broad, then narrow; prefer primary/authoritative sources
  over SEO content farms. See the tool map.
- **Output contract:** a compressed, factual summary where every claim is followed by
  the URL of a **primary/authoritative source the agent actually opened** — not a
  search-result snippet. No raw page dumps.
- **Boundaries:** what's out of scope, and roughly how many sources to gather.

**If a source can't be fetched** (block, paywall, TLS error): try an authoritative
**mirror** (Microsoft Learn mirrors Azure-hosted OpenAI behavior; `context7` serves
vendor SDK/API docs) — do **not** silently fall back to search snippets. Any claim
left resting only on a secondary summary or an unreachable page must be marked
**unverified** in step 4.

### 4. Verify (the part that makes it trustworthy)
For each claim you intend to cite, confirm the source actually supports it. A claim is
**Verified** only if its supporting source was actually fetched in this session.
Claims resting only on search snippets or pages you couldn't open are **flagged** —
still cited, but called out. **Drop** any claim no source supports, and any citation
you can't trace to a real source you retrieved. Fabricated or snippet-only citations
hide in long reports — this pass is non-negotiable.

### 5. Write
Synthesize (don't concatenate) into Markdown:
- H1 title + a 2–4 sentence executive summary.
- Body sections that **integrate across** sub-questions.
- `[n]` citation markers on every factual claim.
- A **Sources** list (`[n]` → title + URL) built only from sources you actually used;
  mark any flagged (snippet-only / unfetchable) source as such.
- A short **Verification** note: how many claims you checked, which are verified vs.
  flagged, and anything dropped.

Offer to save the report to a file when it's long.

## Tool map (this environment)

- **General web:** `WebSearch` → `WebFetch` for full pages. If `WebFetch` is blocked or
  fails, use a mirror (below) or `firecrawl` — don't downgrade to snippets silently.
  `firecrawl` (Bifrost) also handles JS-rendered / auth-walled pages and whole-site crawls.
- **Library / API docs:** `context7` (resolve-library-id → query-docs) for exact
  signatures — **and as a fallback when a vendor's own site is unreachable.**
- **Microsoft + Azure-hosted models:** `microsoft_learn` for .NET / Azure — **and as an
  authoritative mirror for Azure-hosted OpenAI model behavior** when openai.com is blocked.
- **Academic:** WebSearch over arxiv.org; Hugging Face `paper_search`.
- **Code / repos:** `gh search repos` / `gh search code`; the GitHub Bifrost server for
  multi-step repo exploration.
- **Video:** `YouTube` (Bifrost) for transcripts and conference talks.
- **Community sentiment (Reddit):** use the `reddit_search` tool (Bifrost, Apify-backed) — it returns Reddit posts/bodies/upvotes without Reddit API creds and bypasses Reddit's bot block. Also good: Hacker News (WebSearch + the HN Algolia API) and GitHub issues. (The legacy official-API `Reddit` MCP is blocked — prefer `reddit_search`.)
- **Tangled trade-offs:** `sequential_thinking` (Bifrost) to reason through hard choices.

## Common mistakes

- Spawning 5 agents for a simple question — gauge first.
- Letting sub-agents return raw pages — demand compressed summaries (context bloat).
- Citing a search snippet as if you read the source — only Verified (fetched) claims
  count as fact; flag the rest.
- Silently falling back to snippets when the primary source won't load — use a mirror.
- A "Sources" list containing URLs you never actually opened.
- Skipping scope on an ambiguous request — produces shallow, off-target reports.
- Sub-agents researching the same angle — make sub-questions genuinely independent.
