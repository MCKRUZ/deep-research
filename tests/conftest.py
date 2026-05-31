"""Shared test fixtures: a fake search provider and a stateful pipeline router
that drives the whole pipeline deterministically with no network."""

from __future__ import annotations

import json
from typing import Any

import pytest

from research_agent.config import Settings
from research_agent.llm.base import LLMResponse, Message, ToolSpec
from research_agent.llm.fake import FakeLLMClient, text_response, tool_response
from research_agent.models import SearchResult, SourceType


class FakeProvider:
    def __init__(self, name: str = "fake", results: list[SearchResult] | None = None) -> None:
        self.name = name
        self.source_type = SourceType.web
        self._results = results or [
            SearchResult(
                title="Source A", url="http://a.example/1", content="Alpha content about X.",
                source_type=SourceType.web,
            ),
            SearchResult(
                title="Source B", url="http://b.example/2", content="Beta content about Y.",
                source_type=SourceType.web,
            ),
        ]
        self.calls: list[str] = []

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        self.calls.append(query)
        return self._results[:limit]


def _has_tool_result(messages: list[Message]) -> bool:
    for m in messages:
        content = m.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    return True
    return False


def pipeline_router(
    *, sub_questions: list[str] | None = None, supported: bool = True
):
    sub_questions = sub_questions or ["What is X?", "What is Y?"]

    def route(system: str, messages: list[Message], model: str, tools: list[ToolSpec] | None):
        s = system.lower()
        if "clarifying questions" in s:
            return text_response(json.dumps({"questions": []}))
        if "research brief" in s:
            return text_response(
                json.dumps(
                    {
                        "objective": "Understand X and Y.",
                        "sub_questions": sub_questions,
                        "scope_notes": "concise",
                    }
                )
            )
        if "triage research queries" in s:
            return text_response(json.dumps({"tier": "standard", "reason": "few angles"}))
        if "research sub-agent" in s:
            if not _has_tool_result(messages):
                return tool_response("fake_search", {"query": "broad query"})
            return text_response("Key finding grounded in evidence (http://a.example/1).")
        if "research writer" in s:
            return text_response(
                "# Report on X and Y\n\nExecutive summary of findings.\n\n"
                "## Findings\nX is alpha [1]. Y is beta [2]."
            )
        if "verify whether a claim" in s:
            return text_response(json.dumps({"supported": supported, "note": "checked"}))
        if "research evaluator" in s:
            return text_response(
                json.dumps(
                    {
                        "factual_accuracy": 4,
                        "citation_accuracy": 4,
                        "completeness": 4,
                        "source_quality": 4,
                        "notes": "solid",
                    }
                )
            )
        return text_response("")

    return route


@pytest.fixture
def settings() -> Settings:
    return Settings(ANTHROPIC_API_KEY="test-key")


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def pipeline_client() -> FakeLLMClient:
    return FakeLLMClient(router=pipeline_router())
