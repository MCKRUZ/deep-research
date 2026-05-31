from __future__ import annotations

import json

from research_agent.llm.fake import FakeLLMClient, text_response
from research_agent.models import Brief, Citation, Claim, ComplexityTier, SourceType, Usage
from research_agent.pipeline.report import assemble_markdown, build_report
from research_agent.pipeline.scope import build_brief, generate_questions
from research_agent.state import RunStore, new_run_id


def test_assemble_markdown_includes_sources_and_flags():
    citations = [Citation(id=1, url="http://u", title="T", source_type=SourceType.web)]
    claims = [Claim(text="dubious [1]", citation_ids=[1], supported=False, verifier_note="bad")]
    md = assemble_markdown("# Body\n\nClaim [1].", citations, claims)
    assert "## Verification" in md
    assert "Flagged" in md
    assert "## Sources" in md
    assert "http://u" in md


def test_build_report_wraps_markdown():
    brief = Brief(query="q", objective="o")
    report = build_report(
        brief=brief, body="# B [1]",
        citations=[Citation(id=1, url="http://u", title="T", source_type=SourceType.web)],
        claims=[Claim(text="B [1]", citation_ids=[1], supported=True)],
        tier=ComplexityTier.simple, usage=Usage(input_tokens=1, output_tokens=2),
    )
    assert report.tier is ComplexityTier.simple
    assert "## Sources" in report.markdown


def test_run_store_roundtrip(tmp_path):
    store = RunStore(str(tmp_path), "r1")
    brief = Brief(query="q", objective="o")
    assert not store.exists("brief")
    store.save_json("brief", brief)
    assert store.exists("brief")
    assert store.load_json("brief", Brief).query == "q"


def test_new_run_id_is_unique():
    assert new_run_id() != new_run_id()


async def test_generate_questions_parses_list(settings):
    client = FakeLLMClient(responses=[text_response(json.dumps({"questions": ["a?", "b?"]}))])
    qs, _ = await generate_questions(client, settings, "topic")
    assert qs == ["a?", "b?"]


async def test_build_brief_parses_objective_and_subquestions(settings):
    client = FakeLLMClient(
        responses=[
            text_response(json.dumps({"objective": "obj", "sub_questions": ["a", "b"], "scope_notes": "n"}))
        ]
    )
    brief, _ = await build_brief(client, settings, "q", [])
    assert brief.objective == "obj"
    assert brief.sub_questions == ["a", "b"]


async def test_build_brief_falls_back_when_empty(settings):
    client = FakeLLMClient(responses=[text_response(json.dumps({"objective": "", "sub_questions": []}))])
    brief, _ = await build_brief(client, settings, "raw query", [])
    assert brief.objective == "raw query"
    assert brief.sub_questions == ["raw query"]


async def test_build_brief_degrades_on_list_json(settings):
    # Regression: non-dict JSON must degrade to a query-only brief, not crash.
    client = FakeLLMClient(responses=[text_response(json.dumps(["x", "y"]))])
    brief, _ = await build_brief(client, settings, "raw query", [])
    assert brief.objective == "raw query"
    assert brief.sub_questions == ["raw query"]
