# research-agent

An adaptive multi-agent research CLI that produces **citation-verified** Markdown
reports. Built on the Anthropic Messages API.

It runs a four-stage pipeline — **Scope → Research → Verify → Write** — with an
orchestrator that fans out parallel sub-agents, gated by a complexity classifier
so trivial queries don't pay the multi-agent token tax. Every cited claim is
checked against its source before the report ships.

## Why it's built this way

See `docs/superpowers/specs/2026-05-31-research-agent-design.md` (design) and
`docs/adr/0001-orchestration-on-anthropic-sdk.md` (why we own the orchestration
instead of leaning on the Claude Code CLI engine).

## Install

```bash
python -m pip install -e ".[dev]"
```

Requires Python ≥ 3.11.

## Configure

Copy `.env.example` to `.env` and fill in what you have:

```
ANTHROPIC_API_KEY=sk-ant-...     # required
TAVILY_API_KEY=tvly-...          # optional: best web search
SEARXNG_URL=http://localhost:8080 # optional: free self-hosted web search
GITHUB_TOKEN=ghp_...             # optional: higher GitHub rate limits
```

Only `ANTHROPIC_API_KEY` is required. arXiv, Semantic Scholar, and GitHub work
without keys (GitHub is rate-limited without a token). No secret is ever
hardcoded; all come from the environment or `.env`.

## Use

```bash
# Interactive: asks up to 3 clarifying questions, then runs autonomously
research "Compare vector databases for RAG at scale"

# Non-interactive (scripting): skip clarification
research "What is retrieval-augmented generation?" --yes

# Budget knob: low | medium | high
research "Survey autonomous research agents in 2026" --effort high

# Also write the report to a path
research "..." --yes --out report.md
```

Each run writes artifacts to `runs/<run-id>/`:

- `report.md` — the final cited report
- `report.json` — structured report (citations, verified claims, usage)
- `trace.json` — tier, budget, sources, cost (no source contents)
- stage checkpoints (`brief.json`, …)

## Evaluate

```bash
research-eval                # run the LLM-as-judge harness over seed queries
research-eval --out eval.json
```

Scores each report on a 1–5 rubric (factual accuracy, citation accuracy,
completeness, source quality) and reports per-case and mean scores. Seed queries
live in `src/research_agent/eval/seeds.py` — add your real queries over time.

## Architecture

```
research "<q>"
   │
   ▼ Scope        clarify (≤3 Qs) → research brief (north star)
   ▼ Classify     complexity tier → budget (sub-agent count, tool/token caps)
   ▼ Research     orchestrator (Opus) → parallel sub-agents (Sonnet) → compress
   ▼ Verify       every cited claim checked against its source; unsupported flagged
   ▼ Write        synthesize cited report; authoritative Sources appended from data
   ▼
report.md + trace
```

### Module map

| Module | Role |
|---|---|
| `llm/base.py` | `LLMClient` protocol, tool/message types |
| `llm/anthropic_client.py` | production client (Messages API, retries, cost) |
| `llm/fake.py` | deterministic test client |
| `llm/agent.py` | the bounded tool-use loop + JSON helpers |
| `pipeline/scope.py` | clarifier + brief |
| `pipeline/classifier.py` | complexity gate + budgets |
| `pipeline/orchestrator.py` | parallel fan-out + source merge |
| `pipeline/subagent.py` | one sub-agent's research loop |
| `pipeline/verify.py` | citation-faithfulness pass |
| `pipeline/write.py` | report synthesis |
| `pipeline/report.py` | final Markdown assembly |
| `tools/` | swappable search providers (arXiv, Semantic Scholar, GitHub, Tavily, SearXNG) |
| `eval/` | LLM-as-judge harness + rubric + seeds |
| `state.py` | run checkpoints + artifacts |

## Test

```bash
python -m pytest -q
```

No network or API keys needed — the suite runs entirely on the fake client and
mocked HTTP.

## Cost note

Uses per-token Anthropic API billing. Model IDs and price estimates are
configurable in `config.py`. The complexity gate is the primary cost lever:
simple queries stay single-agent; only broad, open-ended research fans out.

## Roadmap (phase 2)

API service, mid-run steering, local/non-Claude models via the `LLMClient` seam,
PDF export, `--resume` wiring, and a larger eval set.
