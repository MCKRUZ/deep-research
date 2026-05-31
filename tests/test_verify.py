from __future__ import annotations

import json

from research_agent.llm.fake import FakeLLMClient, text_response
from research_agent.models import Claim
from research_agent.pipeline.verify import extract_claims, unsupported, verify_claims


def test_extract_claims_finds_cited_sentences():
    md = "Intro with no cite. X is alpha [1]. Y is beta [2][3]. Trailing."
    claims = extract_claims(md)
    assert len(claims) == 2
    assert claims[0].citation_ids == [1]
    assert claims[1].citation_ids == [2, 3]


def test_extract_claims_ignores_uncited_text():
    assert extract_claims("No citations here at all.") == []


async def test_verify_flags_unsupported(settings):
    client = FakeLLMClient(
        router=lambda *a: text_response(json.dumps({"supported": False, "note": "not in source"}))
    )
    claims = [Claim(text="bogus claim", citation_ids=[1])]
    out, usage = await verify_claims(client, settings, claims, {1: "unrelated source text"})
    assert out[0].supported is False
    assert unsupported(out) == out
    assert usage.output_tokens > 0


async def test_verify_marks_supported(settings):
    client = FakeLLMClient(
        router=lambda *a: text_response(json.dumps({"supported": True, "note": "ok"}))
    )
    claims = [Claim(text="good claim", citation_ids=[1])]
    out, _ = await verify_claims(client, settings, claims, {1: "supporting text"})
    assert out[0].supported is True
    assert unsupported(out) == []
