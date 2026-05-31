"""Pipeline entrypoint: classify -> research -> write -> verify -> assemble.

Takes a ready ``Brief`` (the CLI collects clarifications first; eval builds one
autonomously) and runs the cost-gated pipeline to a verified ``Report``.
Checkpoints each stage to the optional ``RunStore``.
"""

from __future__ import annotations

from research_agent.config import Settings
from research_agent.llm.base import LLMClient
from research_agent.models import Brief, ComplexityTier, EffortLevel, Report, Usage
from research_agent.pipeline import classifier, report as report_mod, verify, write
from research_agent.pipeline.orchestrator import run_research
from research_agent.state import RunStore
from research_agent.tools.base import ToolRegistry


async def build_brief_autonomous(
    client: LLMClient, settings: Settings, query: str
) -> tuple[Brief, Usage]:
    from research_agent.pipeline.scope import build_brief

    return await build_brief(client, settings, query, [])


async def run_pipeline(
    client: LLMClient,
    settings: Settings,
    brief: Brief,
    registry: ToolRegistry,
    *,
    effort: EffortLevel = EffortLevel.medium,
    store: RunStore | None = None,
    seed_usage: Usage | None = None,
) -> Report:
    usage = seed_usage or Usage()

    if store:
        store.save_json("brief", brief)

    tier, u = await classifier.classify(client, settings, brief)
    usage = usage.add(u)
    budget = classifier.budget_for(tier, effort)

    bundle = await run_research(client, settings, brief, registry, budget)
    usage = usage.add(bundle.usage)

    body, u = await write.write_report(client, settings, brief, bundle)
    usage = usage.add(u)

    claims = verify.extract_claims(body)
    claims, u = await verify.verify_claims(client, settings, claims, bundle.source_text)
    usage = usage.add(u)

    report = report_mod.build_report(
        brief=brief,
        body=body,
        citations=bundle.citations,
        claims=claims,
        tier=tier,
        usage=usage,
    )

    if store:
        md_path = store.write_report(report)
        store.write_trace(
            {
                "run_id": store.run_id,
                "query": brief.query,
                "tier": tier.value,
                "effort": effort.value,
                "budget": budget.model_dump(),
                "sub_questions": brief.sub_questions,
                "sources": len(report.citations),
                "claims_checked": len([c for c in claims if c.supported is not None]),
                "claims_flagged": len([c for c in claims if c.supported is False]),
                "usage": report.usage.model_dump(),
                "report_path": str(md_path),
            }
        )

    return report


# Compatibility alias for the tier enum re-export
__all__ = ["run_pipeline", "build_brief_autonomous", "ComplexityTier"]
