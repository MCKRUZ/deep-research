# deep-research

A Claude Code **skill** that turns any "research X for me" request into a
**citation-verified report**. It scopes the question, fans out parallel research
sub-agents proportional to complexity, verifies every citation against its source,
then synthesizes — all inside your normal Claude Code session, on your
subscription, using the tools and MCP servers you already have.

> This project began as a standalone Python app (Anthropic Messages API). It was
> retired in favor of a skill — same playbook, zero infrastructure, no API
> billing, native sub-agents. See `docs/adr/0002-pivot-to-claude-code-skill.md`
> for the why. The app is recoverable from git history (commit `3203ee2`) if a
> headless/scheduled service is ever needed.

## What's here

| Path | What it is |
|---|---|
| `skills/deep-research/SKILL.md` | The skill (version-controlled source). |
| `docs/superpowers/specs/…-design.md` | Original architecture/design spec. |
| `docs/adr/0001-…` | Why orchestration was built on the Anthropic API (app era). |
| `docs/adr/0002-…` | Why we pivoted from app → skill. |
| `_research/` | Primary sources gathered while designing (Anthropic multi-agent, OpenAI/Tongyi deep research, STORM, LangChain ODR, search-backend comparisons). |

## Install

The skill is installed at `~/.claude/skills/deep-research/SKILL.md`. To reinstall
from this repo, copy it there:

```bash
cp skills/deep-research/SKILL.md ~/.claude/skills/deep-research/SKILL.md
```

(On Windows: `Copy-Item skills\deep-research\SKILL.md $HOME\.claude\skills\deep-research\SKILL.md`.)

## Use

Just ask, in any Claude Code session:

- "Research the current landscape of vector databases for RAG at scale."
- "Go deep on how Anthropic and OpenAI differ on prompt caching."
- "Compare LangGraph, CrewAI, and Pydantic AI for building agents."

Claude loads the skill and runs **Scope → Gauge → Research → Verify → Write**,
returning a Markdown report with `[n]` citations, a Sources list, and a short
verification note. It asks up to 3 clarifying questions first unless you say
"just go."

## The playbook (what the skill encodes)

1. **Scope** — clarify, then compress to an objective + independent sub-questions.
2. **Gauge** — simple/standard/deep → 0 / 2–3 / 4–6 parallel sub-agents (don't over-spawn).
3. **Research** — one `Task` sub-agent per sub-question, concurrent, each returning compressed cited findings.
4. **Verify** — every cited claim checked against its source; unsupported claims flagged.
5. **Write** — synthesize a cited report with a Sources list and verification note.

Grounded in the patterns from `_research/`: Anthropic's orchestrator-worker
multi-agent system, the Scope→Research→Write shape from LangChain Open Deep
Research, STORM's report synthesis, and rubric-based evaluation.
