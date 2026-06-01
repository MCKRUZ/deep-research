# Community Sentiment: Building Deep Research Agents

> Source note: Reddit was unreachable in this environment (API 403 / anti-bot on every
> path). Substituted Hacker News (HN Algolia API, ~110 comments across 10 threads),
> GitHub issues (`assafelovic/gpt-researcher`, `langchain-ai/open_deep_research`), and
> practitioner/vendor blogs. HN over-indexes skeptical/technical voices — negative
> sentiment is likely amplified vs. a general-user sample. Gathered 2026-05-31.

## 1. Tools — recommended vs. overhyped

No single winner; choice is task-dependent.

- **OpenAI Deep Research** — "narrow and deep," best for serious work, premium price, still
  hallucinates. ~20 high-quality sources, 20-50pp. Mixed-positive. (HN 43236184)
- **Perplexity Deep Research** — "shallow and broad," fast (2-4 min), free tier, reliable
  inline cites, but takes sources at face value. Mixed. (HN 43061827)
- **Gemini Deep Research** — cheaper, weak source quality, "clumsy at tool use." Mixed-neg. (HN 45199256)
- **GPT Researcher** — default OSS recommendation (~$0.40/run o3-mini, ~5 min). Positive, but cost gotchas (§3).
- **STORM** — academically respected, "verbose and shallow" in practice. Mixed. (HN 41553875)
- **LangChain Open Deep Research** — good reference architecture; repo issues dominated by dep bumps + token truncation.
- **Tongyi DeepResearch** — small open model claims to beat OpenAI/Gemini on GAIA/BrowseComp; skeptical-curious. (HN 45789602)
- **Anthropic multi-agent Research** — cited as the credible source of architecture best-practices.

Overhyped (strong signal): the "openTHING clone" pattern ("makers overhype superficial repros,
trivialize the last mile" — swyx, HN 42937701); the "Deep Research"/"PhD-level" branding itself
(HN 45789602, 42913251).

## 2. Criticisms & gotchas

- **Hallucinated / uncritically-weighted citations** (strongest signal, every thread). Fake refs
  hide in long reports; models ignore source connotation; SEO-poisoning of sources will worsen
  trust (HN 43133207). Corroborated by 2026 eval literature — 3-13% fabricated URLs, no DRA robustly
  reliable (arxiv 2604.03173).
- **Shallow synthesis / "bland consulting report"** (HN 45789602). Counter-view: great for source
  discovery, not final answers (HN 43236184).
- **Cost / token blowup** — GitHub gpt-researcher issues #1782/#1535/#1671 (budgets, plan manager,
  checkpointing); LangChain blog calls cost an open problem.
- **Latency** — OpenAI 5-30 min, Gemini <15, Perplexity 2-4 (Helicone). LangChain: "users don't
  want simple requests to take 10+ minutes."
- **Reliability / tool-use failures** — a named reason people pay vs self-host; open_deep_research
  #272 (truncation), #269 (unbounded revision loop).
- **Eval difficulty** — gpt-researcher #1690/#1727; GAIA is de-facto but distrusted.

## 3. Build vs. buy

Leans "buy the frontier product, build only the orchestration." Open clones can't replicate the
RL-trained frontier model (HF Open Deep Research 54% GAIA vs OpenAI 67% — "lack o3"). Commoditized
by the labs (HN 43061827). Build where data-locality/custom corpora force it — connect to
Confluence/Jira/Slack/Drive, data stays local (HN 43242551). Use GPT-Researcher / LangChain ODR as
scaffolding, not the brain.

## 4. Consensus best practices

1. Treat output as a launchpad, not an answer; verify citations yourself.
2. Use for source discovery & breadth; do depth/judgment yourself.
3. Start broad, then narrow (Anthropic guidance).
4. Parallelize subagents/tool calls (Anthropic: up to 90% time reduction).
5. Match strategy to query type (LangChain taxonomy: comparison / listing / validation).
6. Scope narrowly and iterate prompts.
7. Build cost/budget guardrails + checkpointing from the start.

## Bottom line

Practitioners are **useful-but-distrustful**: today's deep-research agents are excellent research
*accelerators / source-finders* and poor *autonomous researchers* — the failure modes (hidden fake
citations, uncritical source weighting, bland synthesis) attack the exact thing the name promises.
Buy the frontier product for general work; build only for data-locality; never ship output unverified.

**This validates the deep-research skill's design choices:** the mandatory citation-faithfulness
(Verify) pass and "Verified only if fetched" rule target the #1 community complaint; the complexity
gate targets the cost/latency complaints; "start broad then narrow" and parallel sub-agents are in
the skill already.

---

## Reddit signal (added 2026-06-01, via the new Apify `reddit_search`)

> Method: 5 site-wide searches via the Apify Fast Reddit Scraper (post-level, no comments),
> 45 posts. Site-wide relevance ranking pulled in noise (viral AI posts unrelated to building
> research agents); below is the on-topic subset. A subreddit-targeted pull (r/LocalLLaMA,
> r/LLMDevs, r/AI_Agents) would be cleaner next time.

**Reddit largely echoes HN/GitHub, and adds two things:**

1. **Open-source deep-research is catching up — and Reddit is excited about it.** Two of the
   highest-signal on-topic posts are open-model wins: **ROMA** ("open-source Deep Research repo
   beats every existing closed-source platform on Seal-0 and FRAMES" — *recursion + multi-agent +
   search tool*, r/LocalLLaMA, 926↑/119c) and **Alibaba Tongyi DeepResearch** ("first fully
   open-source Web Agent on par with OpenAI Deep Research, 30B / 3B active", r/singularity, 407↑).
   Sentiment: genuine enthusiasm that small open models now rival billion-dollar closed ones —
   more bullish on OSS than HN, which was skeptical of "openTHING clones."

2. **A strong "stop over-engineering your agents" backlash** — the standout opinion post:
   r/AI_Agents, *"Stop building complex fancy AI Agents"* (374↑/95c) from a builder of 25+ agents:
   "most of you are building **Rube Goldberg machines when you need a hammer**." This directly
   echoes HN's "openTHING clones disappoint" and Anthropic's "don't build an agent when a workflow
   will do" — the **gauge-complexity-first** discipline is community-validated from three independent
   sources now.

**Reinforced (consistent with HN/GitHub):**
- **Hallucination/reliability anxiety is pervasive** across r/ChatGPT and friends (the AI-court-
   filing hallucination saga, the fabricated-disease-believed-by-AI post) — reinforces the #1 gotcha:
   never ship unverified output. Tool roundups flag it too (r/ChatGPTPro "Best AI Tools 2026": Manus
   "can hallucinate on long research").
- **Perplexity Deep Research** is actively marketed as SOTA on Law/Medicine/Academic (r/perplexity_ai,
   408↑) — vendor framing; treat as directional, same mixed pattern HN reported.

**Net:** Reddit confirms the picture and is the most positive of the three sources on open-source
deep-research agents (ROMA, Tongyi), while independently validating the "don't over-build" and
"verify everything" lessons the skill already encodes.
