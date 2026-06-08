# deep-research-plus

A Claude Code **skill** that turns any "research X for me" request into a
**citation-verified report — with community sentiment and a polished HTML deliverable**.
It delegates the core search → verify → synthesis to Claude Code's **built-in
`deep-research` workflow**, then adds the pieces that workflow lacks: user-facing scoping,
Reddit/community sentiment, a self-contained HTML report, and an organized on-disk output
folder.

> **Lineage.** This began as a standalone Python app on the Anthropic Messages API
> (ADR 0001), was retired in favor of a self-contained prose skill (ADR 0002), and is now
> a thin **wrapper over Anthropic's built-in deep-research workflow** (ADR 0003) — same
> methodology, far less to maintain, plus our environment-specific value. Each prior form
> is recoverable from git history.

## What's here

| Path                                             | What it is                                                                                                                                       |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `skills/deep-research-plus/SKILL.md`             | The skill (version-controlled source).                                                                                                           |
| `skills/deep-research-plus/report-template.html` | Self-contained HTML report template.                                                                                                             |
| `docs/adr/0001-…`                                | Why orchestration was built on the Anthropic API (app era).                                                                                      |
| `docs/adr/0002-…`                                | Why we pivoted from app → skill.                                                                                                                 |
| `docs/adr/0003-…`                                | Why we now wrap the built-in deep-research workflow.                                                                                             |
| `docs/superpowers/specs/…`                       | Original architecture/design specs.                                                                                                              |
| `_research/`                                     | Primary sources gathered while designing (Anthropic multi-agent, OpenAI/Tongyi deep research, STORM, LangChain ODR, search-backend comparisons). |

## How it works

`deep-research-plus` runs **Scope → Delegate → Sentiment → Synthesize → Render → Save**:

1. **Scope** — clarify (≤3 questions unless you say "just go"), compress to a refined question.
2. **Delegate** — invoke the built-in workflow: `Workflow({name:"deep-research", args:"<question>"})`.
   It runs the deterministic 5-angle fan-out → fetch 15 sources → 3-vote adversarial
   verification → synthesis, and returns structured findings + sources.
3. **Sentiment** — `reddit_search` (Bifrost/Apify) for real-world community signal.
4. **Synthesize** — weave verified findings + sentiment into `report.md` with `[n]` citations.
5. **Render** — a self-contained `report.html` from `report-template.html`.
6. **Save** — to `research/YYYY-MM-DD-<slug>/`, and report the exact paths.

The built-in workflow runs on your Claude subscription (no separate API key). The trade-off
of wrapping it: it's fixed-cost (always 5 angles / 15 sources / 3 votes), and the skill
couples to its name + return shape — small blast radius, since the skill reads whatever
JSON returns and adapts. See ADR 0003 for the full rationale.

## Install

Copy the skill into your Claude Code skills directory:

```bash
cp -r skills/deep-research-plus ~/.claude/skills/deep-research-plus
```

(On Windows PowerShell:
`Copy-Item -Recurse -Force skills\deep-research-plus $HOME\.claude\skills\deep-research-plus`.)

## Use

Just ask, in any Claude Code session:

- "Research the current landscape of vector databases for RAG at scale."
- "Go deep on how Anthropic and OpenAI differ on prompt caching."
- "Compare LangGraph, CrewAI, and Pydantic AI for building agents."

Claude scopes the question, runs the built-in pipeline plus a community-sentiment pass,
and writes a cited `report.md` + `report.html` to `research/YYYY-MM-DD-<slug>/`.
