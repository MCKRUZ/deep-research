"""GitHub repository search provider.

API shape verified live on 2026-05-31
(``GET https://api.github.com/search/repositories``): top-level ``items``
array; each item has ``full_name``, ``html_url``, ``description`` (may be
``null``), ``stargazers_count`` (int), and ``language`` (may be ``null``).
The token is optional: unauthenticated requests still work at a lower rate
limit, so we only attach the ``Authorization`` header when a token is set.
"""

from __future__ import annotations

import logging

import httpx

from research_agent.config import Settings
from research_agent.models import SearchResult, SourceType

logger = logging.getLogger(__name__)

_GITHUB_URL = "https://api.github.com/search/repositories"


class GitHubProvider:
    name = "github"
    source_type = SourceType.code

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        params = {"q": query, "per_page": limit, "sort": "stars"}
        headers = {"Accept": "application/vnd.github+json"}
        if self._settings.github_token:
            headers["Authorization"] = f"Bearer {self._settings.github_token}"
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._settings.http_timeout_s)
        try:
            response = await client.get(_GITHUB_URL, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()
            return _parse_github(payload)
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("github search failed: %s", exc)
            return []
        finally:
            if owns_client:
                await client.aclose()


def _parse_github(payload: dict) -> list[SearchResult]:
    results: list[SearchResult] = []
    for item in payload.get("items") or []:
        url = item.get("html_url") or ""
        if not url:
            continue
        description = item.get("description") or ""
        stars = int(item.get("stargazers_count", 0) or 0)
        language = item.get("language") or "unknown"
        content = f"{description}\n⭐{stars} · {language}"
        results.append(
            SearchResult(
                title=item.get("full_name") or "",
                url=url,
                content=content,
                source_type=SourceType.code,
                score=float(stars),
            )
        )
    return results
