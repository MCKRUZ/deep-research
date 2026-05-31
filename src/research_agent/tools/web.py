"""Web search providers: Tavily (keyed) and SearXNG (self-hosted, keyless).

API shapes:

* Tavily ``POST https://api.tavily.com/search`` — confirmed live on
  2026-05-31 that the endpoint accepts the ``api_key``-in-body request shape.
  Response is a top-level object with a ``results`` array; each result has
  ``title``, ``url``, ``content``, and ``score`` (float relevance).
* SearXNG ``GET {base}/search?format=json`` — top-level ``results`` array
  with ``title``, ``url``, ``content`` per item (standard SearXNG JSON
  output).
"""

from __future__ import annotations

import logging

import httpx

from research_agent.config import Settings
from research_agent.models import SearchResult, SourceType

logger = logging.getLogger(__name__)

_TAVILY_URL = "https://api.tavily.com/search"


class TavilyProvider:
    name = "tavily"
    source_type = SourceType.web

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        if not self._settings.tavily_api_key:
            return []
        body = {
            "api_key": self._settings.tavily_api_key,
            "query": query,
            "max_results": limit,
            "search_depth": "advanced",
            "include_raw_content": False,
        }
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._settings.http_timeout_s)
        try:
            response = await client.post(_TAVILY_URL, json=body)
            response.raise_for_status()
            payload = response.json()
            return _parse_tavily(payload)
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("tavily search failed: %s", exc)
            return []
        finally:
            if owns_client:
                await client.aclose()


def _parse_tavily(payload: dict) -> list[SearchResult]:
    results: list[SearchResult] = []
    for item in payload.get("results") or []:
        url = item.get("url") or ""
        if not url:
            continue
        results.append(
            SearchResult(
                title=item.get("title") or "",
                url=url,
                content=item.get("content") or "",
                source_type=SourceType.web,
                score=float(item.get("score", 0) or 0),
            )
        )
    return results


class SearxngProvider:
    name = "searxng"
    source_type = SourceType.web

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        if not self._settings.searxng_url:
            return []
        base = self._settings.searxng_url.rstrip("/")
        params = {"q": query, "format": "json"}
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._settings.http_timeout_s)
        try:
            response = await client.get(f"{base}/search", params=params)
            response.raise_for_status()
            payload = response.json()
            return _parse_searxng(payload, limit)
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("searxng search failed: %s", exc)
            return []
        finally:
            if owns_client:
                await client.aclose()


def _parse_searxng(payload: dict, limit: int) -> list[SearchResult]:
    results: list[SearchResult] = []
    for item in (payload.get("results") or [])[:limit]:
        url = item.get("url") or ""
        if not url:
            continue
        results.append(
            SearchResult(
                title=item.get("title") or "",
                url=url,
                content=item.get("content") or "",
                source_type=SourceType.web,
                score=0.0,
            )
        )
    return results
