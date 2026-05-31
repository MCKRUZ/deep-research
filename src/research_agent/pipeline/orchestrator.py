"""Orchestrator: fan out sub-agents in parallel within the budget, then merge.

The hard cap on sub-agent count (from the complexity gate) is enforced here —
this is the guard against the documented "50 sub-agents for a simple query"
failure. Sources are merged into one globally-numbered citation list; the raw
source text is kept in memory (not in the report) for the verifier.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from research_agent.config import Settings
from research_agent.llm.base import LLMClient
from research_agent.models import Brief, Budget, Citation, Finding, Usage
from research_agent.pipeline.subagent import research_subquestion
from research_agent.tools.base import ToolRegistry

# Per-call output cap. The run-level token budget is tracked/reported via Usage;
# the enforced cost levers are sub-agent count and tool calls.
_SUBAGENT_OUTPUT_TOKENS = 4096


@dataclass
class ResearchBundle:
    findings: list[Finding]
    citations: list[Citation]
    source_text: dict[int, str] = field(default_factory=dict)
    usage: Usage = field(default_factory=Usage)


async def run_research(
    client: LLMClient,
    settings: Settings,
    brief: Brief,
    registry: ToolRegistry,
    budget: Budget,
) -> ResearchBundle:
    sub_questions = brief.sub_questions[: budget.max_subagents]
    coros = [
        research_subquestion(
            client,
            settings,
            q,
            registry,
            max_tool_calls=budget.max_tool_calls_per_agent,
            max_tokens=_SUBAGENT_OUTPUT_TOKENS,
        )
        for q in sub_questions
    ]
    sub_results = await asyncio.gather(*coros)

    url_to_id: dict[str, int] = {}
    citations: list[Citation] = []
    source_text: dict[int, str] = {}
    findings: list[Finding] = []
    total = Usage()

    for sr in sub_results:
        total = total.add(sr.usage)
        local_cites: list[Citation] = []
        for res in sr.results:
            cid = url_to_id.get(res.url)
            if cid is None:
                cid = len(citations) + 1
                url_to_id[res.url] = cid
                citations.append(
                    Citation(
                        id=cid, url=res.url, title=res.title, source_type=res.source_type
                    )
                )
                source_text[cid] = res.content
            local_cites.append(citations[cid - 1])
        findings.append(
            Finding(
                sub_question=sr.sub_question,
                summary=sr.summary,
                citations=local_cites,
                raw_results_count=len(sr.results),
            )
        )

    return ResearchBundle(findings=findings, citations=citations, source_text=source_text, usage=total)
