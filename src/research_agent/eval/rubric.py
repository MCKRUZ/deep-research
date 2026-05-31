"""LLM-as-judge rubric scoring.

Research outputs have no single ground-truth string, so we score the final
report against a rubric (end-state, not turn-by-turn). Citation accuracy is
scored separately from content quality because that is where fabricated
citations get caught.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from research_agent.config import Settings
from research_agent.llm.agent import complete_json
from research_agent.llm.base import LLMClient
from research_agent.models import Usage

_MAX_REPORT_CHARS = 12_000


class RubricScore(BaseModel):
    factual_accuracy: int = Field(ge=1, le=5)
    citation_accuracy: int = Field(ge=1, le=5)
    completeness: int = Field(ge=1, le=5)
    source_quality: int = Field(ge=1, le=5)
    notes: str = ""

    @property
    def overall(self) -> float:
        return round(
            (self.factual_accuracy + self.citation_accuracy + self.completeness + self.source_quality)
            / 4,
            2,
        )


_JUDGE_SYSTEM = (
    "You are an expert research evaluator. Score a research report against a "
    "rubric on a 1-5 scale (5 best). Judge the final report only. Reply with ONLY "
    "JSON: {\"factual_accuracy\": n, \"citation_accuracy\": n, \"completeness\": n, "
    "\"source_quality\": n, \"notes\": \"...\"}.\n"
    "- factual_accuracy: are the claims correct and free of hallucination?\n"
    "- citation_accuracy: do the [n] citations actually support their claims and "
    "point to real, relevant sources?\n"
    "- completeness: does it fully address the query and its angles?\n"
    "- source_quality: are sources authoritative and appropriate?"
)


async def judge(
    client: LLMClient, settings: Settings, query: str, report_markdown: str
) -> tuple[RubricScore, Usage]:
    user = f"QUERY:\n{query}\n\nREPORT:\n{report_markdown[:_MAX_REPORT_CHARS]}"
    data, usage = await complete_json(
        client, model=settings.orchestrator_model, system=_JUDGE_SYSTEM, user=user, max_tokens=600
    )

    def _clamp(key: str) -> int:
        try:
            return max(1, min(5, int(data.get(key, 1))))
        except (TypeError, ValueError):
            return 1

    score = RubricScore(
        factual_accuracy=_clamp("factual_accuracy"),
        citation_accuracy=_clamp("citation_accuracy"),
        completeness=_clamp("completeness"),
        source_quality=_clamp("source_quality"),
        notes=str(data.get("notes", "")).strip(),
    )
    return score, usage
