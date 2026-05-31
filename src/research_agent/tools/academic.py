"""Keyless academic search providers: arXiv and Semantic Scholar.

API shapes verified live on 2026-05-31:

* arXiv Atom feed (``https://export.arxiv.org/api/query``): feed default
  namespace is ``http://www.w3.org/2005/Atom``. Each ``<entry>`` carries a
  ``<title>``, a ``<summary>`` (the abstract), an ``<id>`` (the canonical
  abs URL), and ``<link rel="alternate" type="text/html">`` (the html URL).
  Title and summary contain embedded newlines/indentation that must be
  collapsed.
* Semantic Scholar Graph v1 paper search
  (``https://api.semanticscholar.org/graph/v1/paper/search``): top-level
  ``data`` array; each item has ``title``, ``url``, ``year``, ``authors``
  (list of ``{authorId, name}``) and ``abstract`` (which may be ``null``).
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

import httpx

from research_agent.config import Settings
from research_agent.models import SearchResult, SourceType

logger = logging.getLogger(__name__)

_ARXIV_URL = "https://export.arxiv.org/api/query"
_ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}

_S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_S2_FIELDS = "title,abstract,url,year,authors"


def _clean(text: str | None) -> str:
    """Collapse Atom whitespace (newlines + indentation) into single spaces."""
    if not text:
        return ""
    return " ".join(text.split())


class ArxivProvider:
    name = "arxiv"
    source_type = SourceType.academic

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": limit,
        }
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._settings.http_timeout_s)
        try:
            response = await client.get(_ARXIV_URL, params=params)
            response.raise_for_status()
            return _parse_arxiv(response.text)
        except (httpx.HTTPError, ET.ParseError) as exc:
            logger.warning("arxiv search failed: %s", exc)
            return []
        finally:
            if owns_client:
                await client.aclose()


def _parse_arxiv(xml_text: str) -> list[SearchResult]:
    root = ET.fromstring(xml_text)
    results: list[SearchResult] = []
    for entry in root.findall("atom:entry", _ARXIV_NS):
        title = _clean(entry.findtext("atom:title", default="", namespaces=_ARXIV_NS))
        summary = _clean(entry.findtext("atom:summary", default="", namespaces=_ARXIV_NS))
        url = _arxiv_url(entry)
        if not url:
            continue
        results.append(
            SearchResult(
                title=title,
                url=url,
                content=summary,
                source_type=SourceType.academic,
                score=0.0,
            )
        )
    return results


def _arxiv_url(entry: ET.Element) -> str:
    """Prefer the html alternate link; fall back to the entry id."""
    for link in entry.findall("atom:link", _ARXIV_NS):
        if link.get("rel") == "alternate" and link.get("type") == "text/html":
            href = link.get("href")
            if href:
                return href
    return _clean(entry.findtext("atom:id", default="", namespaces=_ARXIV_NS))


class SemanticScholarProvider:
    name = "semanticscholar"
    source_type = SourceType.academic

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        params = {"query": query, "limit": limit, "fields": _S2_FIELDS}
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._settings.http_timeout_s)
        try:
            response = await client.get(_S2_URL, params=params)
            response.raise_for_status()
            payload = response.json()
            return _parse_s2(payload)
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("semanticscholar search failed: %s", exc)
            return []
        finally:
            if owns_client:
                await client.aclose()


def _parse_s2(payload: dict) -> list[SearchResult]:
    results: list[SearchResult] = []
    for item in payload.get("data") or []:
        title = item.get("title") or ""
        abstract = item.get("abstract")
        content = abstract if abstract else title
        url = item.get("url") or ""
        if not url:
            continue
        results.append(
            SearchResult(
                title=title,
                url=url,
                content=content,
                source_type=SourceType.academic,
                score=0.0,
            )
        )
    return results
