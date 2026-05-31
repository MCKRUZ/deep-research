---
name: deep-research
description: Use when the user wants thorough multi-source research synthesized into a cited report — "research X", "go deep on Y", compare A vs B vs C, survey/landscape the state of Z, literature reviews, or technical deep-dives that need many sources reconciled. Not for single-fact lookups answerable in one search.
---

# Deep Research

## Overview

Produce a **citation-verified research report** by scoping the question, fanning out
parallel research sub-agents proportional to complexity, verifying every citation
against its source, then synthesizing. Core principle: **spend effort proportional
to the question, ground every claim in a real source, and never trust an unverified
citation.**

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

### 3. Research — dispatch parallel sub-agents
Launch one `Task` sub-agent per sub-question **in a single message** so they run
concurrently. Give each agent explicitly:
- **Objective + its one sub-question**, and how it serves the overall objective.
- **Source guidance** (see tool map) — start broad, then narrow; prefer primary and
  authoritative sources over SEO content farms.
- **Output contract:** a compressed, factual summary with every claim followed by its
  source URL. No raw page dumps.
- **Boundaries:** what's out of scope, and roughly how many sources to gather.

### 4. Verify (the part that makes it trustworthy)
Before writing, check faithfulness: for each claim you intend to cite, confirm the
source actually supports it. **Drop or flag** any claim its source doesn't substantiate,
and any citation you can't trace to a real source you retrieved. Fabricated citations
hide in long reports — this pass is non-negotiable.

### 5. Write
Synthesize (don't concatenate) into Markdown:
- H1 title + a 2–4 sentence executive summary.
- Body sections that **integrate across** sub-questions.
- `[n]` citation markers on every factual claim.
- A **Sources** list (`[n]` → title + URL) built only from sources you actually used.
- A short **Verification** note: how many claims you checked, and any flagged as unsupported.

Offer to save the report to a file when it's long.

## Tool map (this environment)

- **General web:** `WebSearch` → `WebFetch` for full pages. `firecrawl` (Bifrost) for
  JS-rendered / auth-walled pages or whole-site crawls.
- **Library / API docs:** `context7` (resolve-library-id → query-docs) for exact
  signatures; `microsoft_learn` for .NET / Azure.
- **Academic:** WebSearch over arxiv.org; Hugging Face `paper_search`.
- **Code / repos:** `gh search repos` / `gh search code`; the GitHub Bifrost server for
  multi-step repo exploration.
- **Video:** `YouTube` (Bifrost) for transcripts and conference talks.
- **Community sentiment:** `Reddit` (Bifrost) for real-world experience and gotchas.
- **Tangled trade-offs:** `sequential_thinking` (Bifrost) to reason through hard choices.

## Common mistakes

- Spawning 5 agents for a simple question — gauge first.
- Letting sub-agents return raw pages — demand compressed summaries (context bloat).
- Citing without verifying — the #1 failure mode; always run step 4.
- A "Sources" list containing URLs you never actually read.
- Skipping scope on an ambiguous request — produces shallow, off-target reports.
- Sub-agents researching the same angle — make sub-questions genuinely independent.
