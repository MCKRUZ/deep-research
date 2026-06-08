# ADR 0003: Wrap Claude Code's built-in deep-research workflow

**Date:** 2026-06-08
**Status:** Accepted (supersedes the delivery vehicle in ADR 0002)
**Decider:** user, after reviewing the built-in workflow internals

## Context

ADR 0002 retired the standalone Python app and shipped the methodology as our own prose
Claude Code skill (`deep-research` — a `SKILL.md` that guides Claude to spawn `Task`
sub-agents). Since then, Anthropic shipped a **built-in `deep-research` workflow** in
Claude Code itself.

Investigation (extracting it from the compiled `claude` binary, then a live smoke test)
established three things:

1. It is **not** a `SKILL.md` — it is a **bundled Workflow** (deterministic compiled JS on
   the Workflow engine): Scope → 5 parallel WebSearch angles → fetch top 15 sources →
   3-vote adversarial verification (≥2/3 refutes kill a claim) → synthesis. It returns a
   structured JSON report.
2. It is **callable by name** from our own skill via
   `Workflow({name:"deep-research", args:"<question>"})` — verified, with a known return
   schema (`findings[]`, `sources[]`, `refuted[]`, `caveats`, `openQuestions[]`, `stats`).
3. It runs on the **Claude subscription** (the `agent()` engine — no separate API key), so
   the per-token-billing reason we retired the app in ADR 0002 does not apply to it.

In other words, Anthropic now ships — billing-free — the code-enforced cost-gate +
citation-verification pipeline that ADR 0001's app was built to provide. Our own prose
`deep-research` skill now overlaps ~100% with it in methodology while offering less rigor
(prompt-guided, not code-enforced).

What the built-in does **not** do — and where our IP actually lives:

- WebSearch/WebFetch only — no Bifrost MCP, no Reddit/community sentiment.
- Returns JSON only — no saved Markdown/HTML report, no output-location protocol.
- Does not talk to the user — no clarifying-question scoping.

## Decision

Retire our standalone `deep-research` `SKILL.md`. Ship **`deep-research-plus`** — a thin
orchestration skill that **delegates** search/verify/synthesis to the built-in
`deep-research` workflow, then adds the four pieces the built-in lacks: user-facing
scoping, Reddit/community sentiment (`reddit_search` via Bifrost/Apify), a polished
self-contained HTML report (`report-template.html`), and the deterministic
`research/YYYY-MM-DD-<slug>/` output protocol.

- **Source of truth:** `skills/deep-research-plus/` in this repo (`SKILL.md` +
  `report-template.html`).
- The old `skills/deep-research/` is removed; its only unique asset
  (`report-template.html`) moves into `deep-research-plus/`. Git history preserves the
  prose pipeline if it is ever needed again.
- The distinct name avoids collision with the built-in (`deep-research` vs
  `deep-research-plus`).

## Consequences

- **Positive:** inherit Anthropic's maintained, adversarially-verified pipeline for free;
  far less to maintain (one thin wrapper, no pipeline of our own); keep our environment
  value (MCP sentiment, HTML, output protocol); no name collision with the built-in.
- **Negative / risk:** couples to two undocumented internals — the workflow's **name**
  (`deep-research`) and its **return shape**. Blast radius is small: the consumer is a
  prose `SKILL.md` interpreted at runtime (it reads whatever JSON returns and adapts), not
  rigid code. The only hard dependency is that the built-in keeps the name and returns
  something with findings + sources.
- **Behavioral trade-off:** the built-in is fixed-cost (always 5 angles / 15 sources / 3
  votes — no complexity gauge), so simple questions pay full fan-out. We accepted losing
  the prose skill's flexible 0 / 2–3 / 4–6 tiering in exchange for the built-in's
  maintained rigor.
- **Reversal trigger:** if Anthropic removes/renames the built-in workflow or breaks its
  return contract, fall back to the prose pipeline (recoverable from git history at the
  `deep-research` skill) or revive the app per ADR 0001/0002.
