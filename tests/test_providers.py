"""Provider mapping tests.

Sample payloads mirror the real API shapes verified live on 2026-05-31.
``asyncio_mode = auto`` is set in pyproject, so async tests need no marker.
Each provider is fed a respx-mocked ``httpx.AsyncClient``; we assert correct
SearchResult mapping, ``[]`` on transport/HTTP error, and ``[]`` when the
required key/url is missing.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from research_agent.config import Settings
from research_agent.models import SourceType
from research_agent.tools.academic import ArxivProvider, SemanticScholarProvider
from research_agent.tools.factory import build_registry
from research_agent.tools.github import GitHubProvider
from research_agent.tools.web import SearxngProvider, TavilyProvider

ARXIV_URL = "https://export.arxiv.org/api/query"
S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
GITHUB_URL = "https://api.github.com/search/repositories"
TAVILY_URL = "https://api.tavily.com/search"
SEARXNG_BASE = "https://searx.example.com"

ARXIV_XML = """<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2211.02350v1</id>
    <title>Tierkreis: A Dataflow
      Framework</title>
    <summary>We present Tierkreis, a higher-order
      dataflow graph.</summary>
    <link href="https://arxiv.org/abs/2211.02350v1" rel="alternate" type="text/html"/>
    <link href="https://arxiv.org/pdf/2211.02350v1" rel="related" type="application/pdf"/>
  </entry>
</feed>"""

S2_JSON = {
    "total": 4224364,
    "offset": 0,
    "data": [
        {
            "paperId": "f3d5",
            "url": "https://www.semanticscholar.org/paper/f3d5",
            "title": "Quantum Computing in the NISQ era",
            "year": 2018,
            "authors": [{"authorId": "1", "name": "J. Preskill"}],
            "abstract": "Noisy Intermediate-Scale Quantum technology.",
        },
        {
            "paperId": "ed1c",
            "url": "https://www.semanticscholar.org/paper/ed1c",
            "title": "Quantum computing with Qiskit",
            "year": 2024,
            "authors": [],
            "abstract": None,
        },
    ],
}

GITHUB_JSON = {
    "total_count": 1,
    "incomplete_results": False,
    "items": [
        {
            "full_name": "trimstray/the-book-of-secret-knowledge",
            "html_url": "https://github.com/trimstray/the-book-of-secret-knowledge",
            "description": "A collection of inspiring lists.",
            "stargazers_count": 225722,
            "language": None,
        }
    ],
}

TAVILY_JSON = {
    "query": "test",
    "results": [
        {
            "title": "Example Result",
            "url": "https://example.com/a",
            "content": "Relevant snippet about the topic.",
            "score": 0.93,
        }
    ],
}

SEARXNG_JSON = {
    "query": "test",
    "results": [
        {
            "title": "Searx Hit",
            "url": "https://example.org/b",
            "content": "Some content body.",
        }
    ],
}


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=5.0)


# --- arXiv ---------------------------------------------------------------


@respx.mock
async def test_arxiv_maps_entries():
    respx.get(ARXIV_URL).mock(return_value=httpx.Response(200, text=ARXIV_XML))
    async with _client() as client:
        results = await ArxivProvider(Settings(), client).search("quantum", limit=2)

    assert len(results) == 1
    r = results[0]
    assert r.title == "Tierkreis: A Dataflow Framework"  # whitespace collapsed
    assert r.content == "We present Tierkreis, a higher-order dataflow graph."
    assert r.url == "https://arxiv.org/abs/2211.02350v1"  # html alternate link
    assert r.source_type is SourceType.academic
    assert r.score == 0.0


@respx.mock
async def test_arxiv_returns_empty_on_500():
    respx.get(ARXIV_URL).mock(return_value=httpx.Response(500))
    async with _client() as client:
        assert await ArxivProvider(Settings(), client).search("x") == []


@respx.mock
async def test_arxiv_returns_empty_on_network_error():
    respx.get(ARXIV_URL).mock(side_effect=httpx.ConnectError("boom"))
    async with _client() as client:
        assert await ArxivProvider(Settings(), client).search("x") == []


# --- Semantic Scholar ----------------------------------------------------


@respx.mock
async def test_s2_maps_data_and_null_abstract_falls_back_to_title():
    respx.get(S2_URL).mock(return_value=httpx.Response(200, json=S2_JSON))
    async with _client() as client:
        results = await SemanticScholarProvider(Settings(), client).search("quantum", limit=2)

    assert len(results) == 2
    assert results[0].content == "Noisy Intermediate-Scale Quantum technology."
    assert results[0].url == "https://www.semanticscholar.org/paper/f3d5"
    assert results[0].source_type is SourceType.academic
    # null abstract -> title fallback
    assert results[1].content == "Quantum computing with Qiskit"


@respx.mock
async def test_s2_returns_empty_on_429():
    respx.get(S2_URL).mock(return_value=httpx.Response(429, json={"code": "429"}))
    async with _client() as client:
        assert await SemanticScholarProvider(Settings(), client).search("x") == []


# --- GitHub --------------------------------------------------------------


@respx.mock
async def test_github_maps_items_with_stars_and_null_language():
    route = respx.get(GITHUB_URL).mock(return_value=httpx.Response(200, json=GITHUB_JSON))
    settings = Settings(GITHUB_TOKEN="ghp_secret")
    async with _client() as client:
        results = await GitHubProvider(settings, client).search("cli", limit=1)

    assert len(results) == 1
    r = results[0]
    assert r.title == "trimstray/the-book-of-secret-knowledge"
    assert r.url == "https://github.com/trimstray/the-book-of-secret-knowledge"
    assert r.content == "A collection of inspiring lists.\n⭐225722 · unknown"
    assert r.source_type is SourceType.code
    assert r.score == 225722.0
    # token present -> Authorization header sent
    sent = route.calls.last.request
    assert sent.headers["Authorization"] == "Bearer ghp_secret"
    assert sent.headers["Accept"] == "application/vnd.github+json"


@respx.mock
async def test_github_no_token_omits_auth_header():
    route = respx.get(GITHUB_URL).mock(return_value=httpx.Response(200, json=GITHUB_JSON))
    async with _client() as client:
        await GitHubProvider(Settings(), client).search("cli")
    assert "Authorization" not in route.calls.last.request.headers


@respx.mock
async def test_github_returns_empty_on_500():
    respx.get(GITHUB_URL).mock(return_value=httpx.Response(500))
    async with _client() as client:
        assert await GitHubProvider(Settings(), client).search("x") == []


# --- Tavily --------------------------------------------------------------


@respx.mock
async def test_tavily_maps_results():
    route = respx.post(TAVILY_URL).mock(return_value=httpx.Response(200, json=TAVILY_JSON))
    settings = Settings(TAVILY_API_KEY="tvly-key")
    async with _client() as client:
        results = await TavilyProvider(settings, client).search("test", limit=3)

    assert len(results) == 1
    r = results[0]
    assert r.title == "Example Result"
    assert r.url == "https://example.com/a"
    assert r.content == "Relevant snippet about the topic."
    assert r.score == pytest.approx(0.93)
    assert r.source_type is SourceType.web
    import json

    body = json.loads(route.calls.last.request.content)
    assert body["api_key"] == "tvly-key"
    assert body["query"] == "test"
    assert body["max_results"] == 3
    assert body["search_depth"] == "advanced"
    assert body["include_raw_content"] is False


async def test_tavily_missing_key_returns_empty_without_http():
    # no respx route registered -> any HTTP call would raise; expect short-circuit
    async with _client() as client:
        assert await TavilyProvider(Settings(), client).search("x") == []


@respx.mock
async def test_tavily_returns_empty_on_401():
    respx.post(TAVILY_URL).mock(return_value=httpx.Response(401, json={"detail": "no"}))
    settings = Settings(TAVILY_API_KEY="tvly-key")
    async with _client() as client:
        assert await TavilyProvider(settings, client).search("x") == []


# --- SearXNG -------------------------------------------------------------


@respx.mock
async def test_searxng_maps_results():
    respx.get(f"{SEARXNG_BASE}/search").mock(
        return_value=httpx.Response(200, json=SEARXNG_JSON)
    )
    settings = Settings(SEARXNG_URL=SEARXNG_BASE)
    async with _client() as client:
        results = await SearxngProvider(settings, client).search("test", limit=5)

    assert len(results) == 1
    r = results[0]
    assert r.title == "Searx Hit"
    assert r.url == "https://example.org/b"
    assert r.content == "Some content body."
    assert r.source_type is SourceType.web


async def test_searxng_missing_url_returns_empty():
    async with _client() as client:
        assert await SearxngProvider(Settings(), client).search("x") == []


@respx.mock
async def test_searxng_returns_empty_on_500():
    respx.get(f"{SEARXNG_BASE}/search").mock(return_value=httpx.Response(500))
    settings = Settings(SEARXNG_URL=SEARXNG_BASE)
    async with _client() as client:
        assert await SearxngProvider(settings, client).search("x") == []


# --- Injected client lifecycle -------------------------------------------


@respx.mock
async def test_injected_client_not_closed_by_provider():
    respx.get(ARXIV_URL).mock(return_value=httpx.Response(200, text=ARXIV_XML))
    client = _client()
    await ArxivProvider(Settings(), client).search("quantum")
    assert not client.is_closed  # caller owns injected client
    await client.aclose()


# --- Factory -------------------------------------------------------------


def test_factory_registers_keyless_providers_only():
    registry = build_registry(Settings())
    names = {p.name for p in registry.all()}
    assert names == {"arxiv", "semanticscholar", "github"}
    assert len(registry) == 3


def test_factory_registers_tavily_and_searxng_when_configured():
    settings = Settings(TAVILY_API_KEY="k", SEARXNG_URL="https://searx.example.com")
    names = {p.name for p in build_registry(settings).all()}
    assert names == {"arxiv", "semanticscholar", "github", "tavily", "searxng"}
