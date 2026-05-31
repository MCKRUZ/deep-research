"""Builds the tool registry from settings, registering providers whose
required configuration is present.

arXiv, Semantic Scholar, and GitHub are keyless (GitHub works
unauthenticated) so they are always registered — guaranteeing the registry
is never empty. Tavily registers only when an API key is set; SearXNG only
when a base URL is set.
"""

from __future__ import annotations

from research_agent.config import Settings
from research_agent.tools.academic import ArxivProvider, SemanticScholarProvider
from research_agent.tools.base import ToolRegistry
from research_agent.tools.github import GitHubProvider
from research_agent.tools.web import SearxngProvider, TavilyProvider


def build_registry(settings: Settings) -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(ArxivProvider(settings))
    registry.register(SemanticScholarProvider(settings))
    registry.register(GitHubProvider(settings))

    if settings.tavily_api_key:
        registry.register(TavilyProvider(settings))
    if settings.searxng_url:
        registry.register(SearxngProvider(settings))

    return registry
