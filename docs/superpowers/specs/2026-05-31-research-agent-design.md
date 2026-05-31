# research-agent — Design Spec

**Date:** 2026-05-31
**Status:** Approved (design); pending implementation plan
**Stack:** Python · `claude-agent-sdk` (Anthropic)

## Summary

A CLI tool that performs autonomous, cited research over the open web, academic
sources, and specialized APIs. It uses an adaptive multi-agent architecture: an
Opus orchestrator decomposes a research brief and spawns parallel Sonnet
sub-agents, gated by a complexity classifier so trivial queries do not pay the
~15x token cost of multi-agent fan-out. Output is a citation-verified Markdown
report.

Invocation:

```
research "<query>" [--effort low|medium|high] [--yes] [--format md|pdf] [--resume <run-id>]
```

## Design decisions (locked)

| Decision | Choice | Rationale |
|---|---|---|
| Interface | CLI → Markdown report | Simplest solid foundation; wrappable later (API/TUI/MCP are phase 2). |
| Orchestration | Adaptive multi-agent | Captures Anthropic's ~90% quality win; complexity gate avoids 15x cost on easy queries. |
| Models | Opus orchestrator + Sonnet sub-agents | The exact config Anthropic reported at 90.2% over single-agent Opus. |
| Autonomy | Clarify upfront, then autonomous | Scope phase is the #1 quality lever; `--yes` skips it for scripting. |
| Rigor | Citation-faithfulness pass + LLM-as-judge eval harness | Fabricated citations are the documented top failure mode; eval measures "ultimate." |
| Build approach | Start native SDK subagents (A); escalate to thin custom orchestrator (C) only if the SDK can't enforce the cost gate cleanly | Smallest Claude-native v1 with a defined escape hatch. |
| Sources | Open web + academic + specialized APIs | Per user. Reddit excluded (blocked + low signal-to-effort). |

## Architecture

Pipeline: **Scope → Research → Verify → Write**, plus a standalone **Eval** harness.

```
research "<q>" --effort --yes
        │
        ▼
   CLI (typer): load config, parse flags, render progress (rich)
        │
        ▼
   SCOPE
     clarifier  → ≤3 clarifying questions (skipped by --yes)
     brief      → compress query + answers into research brief (north star)
        │
        ▼
   COMPLEXITY GATE
     classify brief → {simple | standard | deep}
     → sub-agent count, tool-call caps, token budget (also bounded by --effort)
        │
        ▼
   RESEARCH (orchestrator, Opus)
     decompose brief into independent sub-tasks
       ├─▶ sub-agent (Sonnet): tool loop → self-compress  ┐
       ├─▶ sub-agent (Sonnet): tool loop → self-compress  ┤ parallel
       └─▶ sub-agent (Sonnet): tool loop → self-compress  ┘
     collect compressed findings (never raw scraped pages)
        │
        ▼
   VERIFY
     faithfulness pass: each claim ↔ its cited source
     drop/flag unsupported claims and fabricated citations
        │
        ▼
   WRITE
     STORM-style synthesis → cited report.md (+ optional PDF)
        │
        ▼
   report.md  +  run-trace.json (checkpoints, costs, sources)
```

**Cross-cutting invariants:**

- The research brief is passed to every stage as the north star.
- Sub-agents compress findings before returning, so the orchestrator's context
  never fills with raw page content.
- Every stage checkpoints state to disk to support resume-from-failure.

## Components

Each is a focused module with one responsibility, testable in isolation.

| Module | Responsibility | Key dependency |
|---|---|---|
| `cli.py` | parse args, load config, dispatch, render progress | typer, rich |
| `config.py` | env/`.env` → typed settings; API keys never hardcoded | pydantic-settings |
| `scope/clarifier.py` | generate ≤3 clarifying questions, collect answers | Claude SDK |
| `scope/brief.py` | compress query + answers → research brief | Claude SDK |
| `classifier.py` | brief → complexity tier → budgets (sub-agent count, tool/token caps) | Claude SDK |
| `orchestrator.py` | decompose brief, spawn sub-agents, collect findings | Claude Agent SDK (subagents) |
| `subagent.py` | tool-calling research loop + self-compression | Claude Agent SDK |
| `tools/` | swappable providers behind one `SearchProvider` protocol | httpx |
| `verify.py` | claim ↔ source faithfulness check | Claude SDK |
| `write.py` | synthesize cited report (STORM-style perspectives) | Claude SDK |
| `report.py` | render Markdown, optional PDF | weasyprint / pdf skill |
| `state.py` | checkpoint/resume, run-trace, cost accounting | json |
| `eval/` | LLM-as-judge harness, ~20 seed queries, rubric scoring | Claude SDK |

## Tool layer

One `SearchProvider` protocol so backends are interchangeable and registered
keyed/DI-style. The search backend is not the performance bottleneck (token
budget and loop quality dominate), so swapping must be cheap.

- **Web:** Tavily or Exa (full-content, agent-ready) primary; SearXNG fallback
  for cost control. SearXNG is AGPL — self-host only, flagged.
- **Academic:** arXiv API + Semantic Scholar (keyless/cheap).
- **Specialized:** GitHub (REST/`gh`), YouTube via the existing Bifrost MCP server.

All tools return a normalized record `{title, url, content, retrieved_at}` so
sub-agents and the verifier treat every source uniformly.

## Error handling & cost discipline

- **Tool failures:** retry with backoff; on persistent failure, inform the agent
  the tool is down (models adapt well) rather than crashing the run.
- **Budget enforcement:** hard caps per effort tier on sub-agent count, tool
  calls, and tokens; the orchestrator refuses to over-spawn (guards against the
  documented "50 sub-agents for a simple query" failure).
- **Checkpointing:** each stage writes state; `--resume <run-id>` continues a
  failed run without re-spending tokens.
- **Secrets:** all keys from env/`.env`; nothing in code; `.env` git-ignored.
- **Logging:** structured JSON of decisions and costs (never source contents)
  for debugging non-deterministic runs.

## Testing strategy

- **Unit:** classifier tiers, brief compression, `SearchProvider` protocol
  (mocked HTTP), verifier claim-matching, report rendering. 80%+ on new code.
- **Integration:** full pipeline against recorded fixtures (cassettes) — no live
  API calls in CI; asserts a cited report is produced and unsupported claims are
  dropped.
- **Eval (quality, not pass/fail):** LLM-as-judge harness over ~20 seed queries,
  scoring factual accuracy / citation accuracy / completeness / source quality;
  run on demand and tracked over time to compare prompt/architecture changes.

## Out of scope for v1 (YAGNI)

Server/API, web UI, mid-run steering, local/non-Claude models, Reddit source,
multi-turn report refinement. All are clean phase-2 additions on this foundation.

## Open verification item (resolve first in the implementation plan)

The exact `claude-agent-sdk` subagent-spawning and parallel-tool API is
**moderate confidence**. Verify it against the SDK docs as step 1 of the plan.
That verification is the decision point for the A→C escalation: if the native
SDK cannot enforce the complexity gate cleanly, introduce a thin custom
orchestrator layer (approach C) at that single point.

## Reference material

Primary sources saved in `_research/`: Anthropic multi-agent system, OpenAI/
Helicone Deep Research, LangChain Open Deep Research, Stanford STORM, Tongyi
DeepResearch, HuggingFace Open Deep Research, search-backend comparisons.
