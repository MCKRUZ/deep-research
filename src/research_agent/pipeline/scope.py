"""Scope stage: clarify the request, then compress it into a research brief.

The brief is the north star carried through every later stage. Skipping
clarification is the documented #1 cause of shallow research, so the CLI asks
the generated questions up front (unless ``--yes``), then this module folds the
answers into an objective + sub-questions.
"""

from __future__ import annotations

from research_agent.config import Settings
from research_agent.llm.agent import complete_json
from research_agent.llm.base import LLMClient
from research_agent.models import Brief, Clarification, Usage

_CLARIFY_SYSTEM = (
    "You sharpen research requests. Generate at most 3 clarifying questions that "
    "would most reduce ambiguity about scope, depth, or intent. If the request is "
    "already specific, return fewer or an empty list. "
    'Reply with ONLY JSON: {"questions": ["...", "..."]}.'
)

_BRIEF_SYSTEM = (
    "You turn a research request (plus any clarifying Q&A) into a focused research "
    "brief. Reply with ONLY JSON: "
    '{"objective": "one-sentence goal", "sub_questions": ["independent angle", "..."], '
    '"scope_notes": "constraints, exclusions, desired depth"}. '
    "Make sub_questions genuinely independent so they can be researched in parallel. "
    "Use 2-5 sub_questions for normal requests."
)


async def generate_questions(
    client: LLMClient, settings: Settings, query: str
) -> tuple[list[str], Usage]:
    data, usage = await complete_json(
        client, model=settings.utility_model, system=_CLARIFY_SYSTEM, user=query, max_tokens=400
    )
    questions = data.get("questions", []) if isinstance(data, dict) else []
    cleaned = [str(q).strip() for q in questions if str(q).strip()][:3]
    return cleaned, usage


async def build_brief(
    client: LLMClient,
    settings: Settings,
    query: str,
    clarifications: list[Clarification],
) -> tuple[Brief, Usage]:
    qa = "\n".join(f"Q: {c.question}\nA: {c.answer}" for c in clarifications)
    user = f"Research request: {query}\n\nClarifying Q&A:\n{qa or '(none)'}"
    data, usage = await complete_json(
        client, model=settings.subagent_model, system=_BRIEF_SYSTEM, user=user, max_tokens=1200
    )
    objective = str(data.get("objective", query)).strip() or query
    sub_questions = [str(s).strip() for s in data.get("sub_questions", []) if str(s).strip()]
    if not sub_questions:
        sub_questions = [query]
    brief = Brief(
        query=query,
        clarifications=clarifications,
        objective=objective,
        sub_questions=sub_questions,
        scope_notes=str(data.get("scope_notes", "")).strip(),
    )
    return brief, usage
