"""A single research sub-agent: investigate one sub-question, return compressed
findings grounded in the sources it actually retrieved.

Returning raw pages would bloat the orchestrator's context, so the sub-agent
produces a summary and we attach only the source metadata it saw. The raw
content is carried separately (in memory) for the verifier.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from research_agent.config import Settings
from research_agent.llm.agent import run_agent
from research_agent.llm.base import LLMClient
from research_agent.models import SearchResult, Usage
from research_agent.tools.base import ResultCollector, ToolRegistry, make_search_tools

_SYSTEM = (
    "You are a research sub-agent. You are given ONE focused question. Use the "
    "search tools to gather evidence: start with a broad query, then narrow based "
    "on what you find. Prefer authoritative primary sources over SEO content farms. "
    "When you have enough, STOP searching and write a compressed, factual summary "
    "of the answer. Ground every claim in a source and cite the source URL inline "
    "in parentheses. Do not pad; density over length."
)


@dataclass
class SubResult:
    sub_question: str
    summary: str
    results: list[SearchResult] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    tool_calls_made: int = 0


async def research_subquestion(
    client: LLMClient,
    settings: Settings,
    sub_question: str,
    registry: ToolRegistry,
    *,
    max_tool_calls: int,
    max_tokens: int = 4096,
) -> SubResult:
    collector = ResultCollector()
    tools = make_search_tools(registry, collector)
    result = await run_agent(
        client=client,
        model=settings.subagent_model,
        system=_SYSTEM,
        user=f"Research question: {sub_question}",
        tools=tools,
        max_tool_calls=max_tool_calls,
        max_tokens=max_tokens,
    )
    return SubResult(
        sub_question=sub_question,
        summary=result.text,
        results=collector.results,
        usage=result.usage,
        tool_calls_made=result.tool_calls_made,
    )
