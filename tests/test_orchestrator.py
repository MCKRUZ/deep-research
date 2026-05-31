from __future__ import annotations

from research_agent.llm.fake import FakeLLMClient
from research_agent.models import Brief, Budget
from research_agent.pipeline.orchestrator import run_research
from research_agent.tools.base import ToolRegistry
from tests.conftest import FakeProvider, pipeline_router


async def test_run_research_merges_and_dedupes_sources(settings, fake_provider):
    client = FakeLLMClient(router=pipeline_router())
    registry = ToolRegistry()
    registry.register(fake_provider)
    brief = Brief(query="q", objective="o", sub_questions=["What is X?", "What is Y?"])
    budget = Budget(max_subagents=2, max_tool_calls_per_agent=3, max_tokens=10_000)

    bundle = await run_research(client, settings, brief, registry, budget)

    assert len(bundle.findings) == 2
    # both sub-agents saw the same two URLs -> deduped to two global citations
    assert len(bundle.citations) == 2
    assert set(bundle.source_text.keys()) == {1, 2}
    assert bundle.usage.output_tokens > 0


async def test_run_research_respects_subagent_cap(settings, fake_provider):
    client = FakeLLMClient(router=pipeline_router(sub_questions=["a", "b", "c"]))
    registry = ToolRegistry()
    registry.register(fake_provider)
    brief = Brief(query="q", objective="o", sub_questions=["a", "b", "c"])
    budget = Budget(max_subagents=1, max_tool_calls_per_agent=3, max_tokens=10_000)

    bundle = await run_research(client, settings, brief, registry, budget)

    assert len(bundle.findings) == 1  # only one sub-agent spawned despite three questions
