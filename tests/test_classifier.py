from __future__ import annotations

import json

from research_agent.llm.fake import FakeLLMClient, text_response
from research_agent.models import Brief, ComplexityTier, EffortLevel
from research_agent.pipeline.classifier import budget_for, classify


def test_budget_scales_with_tier():
    med = EffortLevel.medium
    assert budget_for(ComplexityTier.simple, med).max_subagents == 1
    assert budget_for(ComplexityTier.standard, med).max_subagents == 3
    assert budget_for(ComplexityTier.deep, med).max_subagents == 4  # deep base 5, capped by medium ceiling 4
    assert budget_for(ComplexityTier.deep, EffortLevel.high).max_subagents == 5


def test_effort_low_caps_subagents_and_shrinks_tokens():
    deep_low = budget_for(ComplexityTier.deep, EffortLevel.low)
    deep_high = budget_for(ComplexityTier.deep, EffortLevel.high)
    assert deep_low.max_subagents <= 2
    assert deep_low.max_tokens < deep_high.max_tokens


async def test_classify_parses_tier(settings):
    client = FakeLLMClient(responses=[text_response(json.dumps({"tier": "deep"}))])
    brief = Brief(query="q", objective="o", sub_questions=["a"])
    tier, usage = await classify(client, settings, brief)
    assert tier is ComplexityTier.deep


async def test_classify_defaults_on_garbage(settings):
    client = FakeLLMClient(responses=[text_response(json.dumps({"tier": "nonsense"}))])
    brief = Brief(query="q", objective="o", sub_questions=["a"])
    tier, _ = await classify(client, settings, brief)
    assert tier is ComplexityTier.standard


async def test_classify_degrades_on_list_json(settings):
    # Regression: a non-dict JSON response must degrade, not crash.
    client = FakeLLMClient(responses=[text_response(json.dumps(["a", "b"]))])
    brief = Brief(query="q", objective="o", sub_questions=["a"])
    tier, _ = await classify(client, settings, brief)
    assert tier is ComplexityTier.standard


async def test_classify_degrades_when_no_valid_json(settings):
    client = FakeLLMClient(responses=[text_response("not json"), text_response("still not")])
    brief = Brief(query="q", objective="o", sub_questions=["a"])
    tier, _ = await classify(client, settings, brief)
    assert tier is ComplexityTier.standard
