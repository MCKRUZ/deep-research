from __future__ import annotations

from research_agent.eval.harness import run_eval
from research_agent.eval.seeds import EvalCase
from research_agent.llm.fake import FakeLLMClient
from research_agent.models import Brief, EffortLevel
from research_agent.pipeline.run import run_pipeline
from research_agent.state import RunStore
from research_agent.tools.base import ToolRegistry
from tests.conftest import FakeProvider, pipeline_router


async def test_run_pipeline_end_to_end(settings, tmp_path):
    client = FakeLLMClient(router=pipeline_router())
    registry = ToolRegistry()
    registry.register(FakeProvider())
    brief = Brief(
        query="explain X and Y", objective="Understand X and Y.",
        sub_questions=["What is X?", "What is Y?"],
    )
    store = RunStore(str(tmp_path), "run1")

    report = await run_pipeline(
        client, settings, brief, registry, effort=EffortLevel.medium, store=store
    )

    assert "## Sources" in report.markdown
    assert "## Verification" in report.markdown
    assert len(report.citations) == 2
    assert report.tier.value == "standard"
    assert report.usage.output_tokens > 0
    assert any(c.supported is True for c in report.claims)
    # artifacts checkpointed
    assert (tmp_path / "run1" / "report.md").exists()
    assert (tmp_path / "run1" / "report.json").exists()
    assert (tmp_path / "run1" / "trace.json").exists()
    assert (tmp_path / "run1" / "brief.json").exists()


async def test_run_eval_scores_cases(settings):
    client = FakeLLMClient(router=pipeline_router())
    registry = ToolRegistry()
    registry.register(FakeProvider())
    cases = [EvalCase(id="c1", query="What is X?")]

    summary = await run_eval(client, settings, registry, cases=cases)

    assert len(summary.cases) == 1
    assert summary.cases[0].overall == 4.0
    assert summary.mean_overall == 4.0
    assert summary.total_usage.output_tokens > 0
