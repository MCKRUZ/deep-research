"""Eval harness: run the pipeline over seed queries and score each with the
rubric judge. Produces a summary you can track over time to compare prompt and
architecture changes.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from research_agent.config import Settings
from research_agent.eval.rubric import RubricScore, judge
from research_agent.eval.seeds import SEEDS, EvalCase
from research_agent.llm.base import LLMClient
from research_agent.models import EffortLevel, Usage
from research_agent.pipeline.run import build_brief_autonomous, run_pipeline
from research_agent.tools.base import ToolRegistry


class CaseResult(BaseModel):
    id: str
    query: str
    tier: str
    score: RubricScore
    overall: float
    sources: int
    flagged_claims: int
    usage: Usage


class EvalSummary(BaseModel):
    cases: list[CaseResult] = Field(default_factory=list)
    mean_overall: float = 0.0
    mean_factual: float = 0.0
    mean_citation: float = 0.0
    mean_completeness: float = 0.0
    mean_source_quality: float = 0.0
    total_usage: Usage = Field(default_factory=Usage)


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


async def run_eval(
    client: LLMClient,
    settings: Settings,
    registry: ToolRegistry,
    *,
    cases: list[EvalCase] | None = None,
    effort: EffortLevel = EffortLevel.medium,
) -> EvalSummary:
    cases = cases if cases is not None else SEEDS
    results: list[CaseResult] = []
    total = Usage()

    for case in cases:
        brief, u = await build_brief_autonomous(client, settings, case.query)
        report = await run_pipeline(
            client, settings, brief, registry, effort=effort, seed_usage=u
        )
        score, ju = await judge(client, settings, case.query, report.markdown)
        case_usage = report.usage.add(ju)
        total = total.add(case_usage)
        results.append(
            CaseResult(
                id=case.id,
                query=case.query,
                tier=report.tier.value,
                score=score,
                overall=score.overall,
                sources=len(report.citations),
                flagged_claims=len([c for c in report.claims if c.supported is False]),
                usage=case_usage,
            )
        )

    return EvalSummary(
        cases=results,
        mean_overall=_mean([r.overall for r in results]),
        mean_factual=_mean([float(r.score.factual_accuracy) for r in results]),
        mean_citation=_mean([float(r.score.citation_accuracy) for r in results]),
        mean_completeness=_mean([float(r.score.completeness) for r in results]),
        mean_source_quality=_mean([float(r.score.source_quality) for r in results]),
        total_usage=total,
    )
