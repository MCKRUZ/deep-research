"""Complexity gate: decide how much parallelism a query earns.

This is the cost-discipline core. A trivial lookup must not pay the ~15x token
tax of multi-agent fan-out, and a broad open-ended question must not be starved.
The classifier picks a tier; ``budget_for`` turns (tier, effort) into hard caps
the orchestrator enforces.
"""

from __future__ import annotations

from research_agent.config import Settings
from research_agent.llm.agent import complete_json
from research_agent.llm.base import LLMClient
from research_agent.models import Brief, Budget, ComplexityTier, EffortLevel, Usage

# Base caps per tier: (max_subagents, max_tool_calls_per_agent, max_tokens)
_BASE: dict[ComplexityTier, tuple[int, int, int]] = {
    ComplexityTier.simple: (1, 3, 20_000),
    ComplexityTier.standard: (3, 5, 60_000),
    ComplexityTier.deep: (5, 8, 150_000),
}

# Effort caps the sub-agent count and scales the token budget.
_EFFORT_SUBAGENT_CEIL: dict[EffortLevel, int] = {
    EffortLevel.low: 2,
    EffortLevel.medium: 4,
    EffortLevel.high: 6,
}
_EFFORT_TOKEN_SCALE: dict[EffortLevel, float] = {
    EffortLevel.low: 0.6,
    EffortLevel.medium: 1.0,
    EffortLevel.high: 1.5,
}


def budget_for(tier: ComplexityTier, effort: EffortLevel) -> Budget:
    subagents, tool_calls, tokens = _BASE[tier]
    subagents = min(subagents, _EFFORT_SUBAGENT_CEIL[effort])
    tokens = int(tokens * _EFFORT_TOKEN_SCALE[effort])
    return Budget(
        max_subagents=max(1, subagents),
        max_tool_calls_per_agent=max(2, tool_calls),
        max_tokens=tokens,
    )


_SYSTEM = (
    "You triage research queries by how much investigation they need. "
    "Reply with ONLY a JSON object: {\"tier\": \"simple|standard|deep\", \"reason\": \"...\"}.\n"
    "- simple: a single fact or definition answerable from one or two sources.\n"
    "- standard: a focused question needing a few independent angles.\n"
    "- deep: broad, open-ended, or comparative research spanning many sub-topics."
)


async def classify(
    client: LLMClient, settings: Settings, brief: Brief
) -> tuple[ComplexityTier, Usage]:
    user = (
        f"Objective: {brief.objective}\n"
        f"Sub-questions: {brief.sub_questions}\n"
        f"Original query: {brief.query}"
    )
    data, usage = await complete_json(
        client, model=settings.utility_model, system=_SYSTEM, user=user, max_tokens=300
    )
    raw = str(data.get("tier", "standard")).lower().strip()
    try:
        tier = ComplexityTier(raw)
    except ValueError:
        tier = ComplexityTier.standard
    return tier, usage
