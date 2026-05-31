"""Seed evaluation queries spanning the complexity tiers and source types.

Start small (Anthropic found ~20 real queries catch large effects). This is a
starter set; add your own real usage queries over time. ``must_mention`` is a
soft signal used in scoring notes, not a hard gate.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    id: str
    query: str
    must_mention: list[str] = Field(default_factory=list)
    notes: str = ""


SEEDS: list[EvalCase] = [
    EvalCase(
        id="simple-def",
        query="What is retrieval-augmented generation (RAG)?",
        must_mention=["retrieval", "context", "generation"],
        notes="simple tier: definitional",
    ),
    EvalCase(
        id="simple-fact",
        query="Who created the STORM research system and at what institution?",
        must_mention=["Stanford"],
        notes="simple tier: single fact",
    ),
    EvalCase(
        id="standard-compare",
        query="Compare Tavily, Exa, and Brave search APIs for use in AI agents.",
        must_mention=["Tavily", "Exa", "Brave"],
        notes="standard tier: comparison",
    ),
    EvalCase(
        id="standard-howto",
        query="What are the core architectural patterns for building a deep research agent?",
        must_mention=["orchestrator", "sub-agent"],
        notes="standard tier: synthesis",
    ),
    EvalCase(
        id="deep-survey",
        query="Survey the state of the art in autonomous multi-agent research systems "
        "in 2025-2026, including evaluation methods.",
        must_mention=["evaluation", "multi-agent"],
        notes="deep tier: broad survey",
    ),
    EvalCase(
        id="academic",
        query="What does the ReAct paper propose and how does it relate to modern agent loops?",
        must_mention=["reasoning", "acting"],
        notes="academic source emphasis",
    ),
    EvalCase(
        id="code",
        query="What are the most popular open-source deep-research agent repositories on GitHub?",
        must_mention=["gpt-researcher"],
        notes="code/github source emphasis",
    ),
    EvalCase(
        id="freshness",
        query="What are the latest developments in LLM-as-judge evaluation for research agents?",
        must_mention=["judge", "rubric"],
        notes="freshness-sensitive",
    ),
]
