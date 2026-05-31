"""Shared data contracts for the research pipeline.

Every stage communicates through these models. They are pydantic models so any
stage's state can be checkpointed to disk with ``model_dump_json`` and resumed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class EffortLevel(str, Enum):
    """User-facing budget knob (``--effort``)."""

    low = "low"
    medium = "medium"
    high = "high"


class ComplexityTier(str, Enum):
    """Classifier output. Drives how much parallelism a query earns."""

    simple = "simple"
    standard = "standard"
    deep = "deep"


class SourceType(str, Enum):
    web = "web"
    academic = "academic"
    code = "code"


class Clarification(BaseModel):
    question: str
    answer: str


class Brief(BaseModel):
    """The north star. Produced by Scope, passed to every downstream stage."""

    query: str
    clarifications: list[Clarification] = Field(default_factory=list)
    objective: str
    sub_questions: list[str] = Field(default_factory=list)
    scope_notes: str = ""
    created_at: datetime = Field(default_factory=_now)


class SearchResult(BaseModel):
    """Normalized record returned by every tool provider."""

    title: str
    url: str
    content: str
    source_type: SourceType
    score: float = 0.0
    retrieved_at: datetime = Field(default_factory=_now)


class Citation(BaseModel):
    id: int
    url: str
    title: str
    source_type: SourceType


class Finding(BaseModel):
    """A sub-agent's compressed contribution back to the orchestrator."""

    sub_question: str
    summary: str
    citations: list[Citation] = Field(default_factory=list)
    raw_results_count: int = 0


class Claim(BaseModel):
    """A factual statement in the report, mapped to its supporting citations."""

    text: str
    citation_ids: list[int] = Field(default_factory=list)
    supported: bool | None = None
    verifier_note: str = ""


class Budget(BaseModel):
    """Hard caps enforced by the orchestrator. Set by classifier + effort."""

    max_subagents: int
    max_tool_calls_per_agent: int
    max_tokens: int


class Usage(BaseModel):
    """Token + cost accounting, aggregated across the run."""

    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def add(self, other: "Usage") -> "Usage":
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cost_usd=round(self.cost_usd + other.cost_usd, 6),
        )


class Report(BaseModel):
    """Final deliverable plus the trace needed to audit it."""

    query: str
    brief: Brief
    markdown: str
    citations: list[Citation] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    tier: ComplexityTier = ComplexityTier.standard
    usage: Usage = Field(default_factory=Usage)
    created_at: datetime = Field(default_factory=_now)
