"""Tool/provider contracts. Frozen interface that providers and the pipeline share.

A ``SearchProvider`` is a swappable retrieval backend. ``make_search_tools`` wraps
the registered providers into ``ToolSpec``s the agent loop can call, while
recording every returned ``SearchResult`` into a ``ResultCollector`` so the
sub-agent can build citations and the verifier can check claims against source
content.
"""

from __future__ import annotations

from typing import Protocol

from research_agent.llm.base import ToolSpec
from research_agent.models import SearchResult, SourceType

_EXCERPT_CHARS = 1200


class SearchProvider(Protocol):
    name: str
    source_type: SourceType

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]: ...


class ResultCollector:
    """Accumulates results seen during a sub-agent run, deduped by URL."""

    def __init__(self) -> None:
        self._by_url: dict[str, SearchResult] = {}

    def add(self, results: list[SearchResult]) -> None:
        for r in results:
            self._by_url.setdefault(r.url, r)

    @property
    def results(self) -> list[SearchResult]:
        return list(self._by_url.values())


class ToolRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, SearchProvider] = {}

    def register(self, provider: SearchProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> SearchProvider:
        return self._providers[name]

    def all(self) -> list[SearchProvider]:
        return list(self._providers.values())

    def __len__(self) -> int:
        return len(self._providers)


def _format(results: list[SearchResult]) -> str:
    if not results:
        return "No results."
    lines: list[str] = []
    for i, r in enumerate(results, 1):
        excerpt = r.content[:_EXCERPT_CHARS].strip()
        lines.append(f"[{i}] {r.title}\n{r.url}\n{excerpt}")
    return "\n\n".join(lines)


def make_search_tools(registry: ToolRegistry, collector: ResultCollector) -> list[ToolSpec]:
    """One ToolSpec per provider, each recording results into the collector."""

    specs: list[ToolSpec] = []
    for provider in registry.all():

        def make_handler(p: SearchProvider):
            async def handler(args: dict) -> str:
                query = str(args.get("query", "")).strip()
                if not query:
                    return "Error: 'query' is required."
                limit = int(args.get("limit", 5))
                results = await p.search(query, limit=limit)
                collector.add(results)
                return _format(results)

            return handler

        specs.append(
            ToolSpec(
                name=f"{provider.name}_search",
                description=(
                    f"Search {provider.source_type.value} sources via {provider.name}. "
                    "Start broad, then narrow. Returns titles, URLs, and excerpts."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query."},
                        "limit": {"type": "integer", "description": "Max results (default 5)."},
                    },
                    "required": ["query"],
                },
                handler=make_handler(provider),
            )
        )
    return specs
