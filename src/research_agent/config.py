"""Typed configuration. Secrets come from the environment or a .env file only.

No API key is ever hardcoded. Model IDs and per-token prices are configurable so
the tool survives model renames and lets the operator correct billing rates.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelPrice(dict):
    """Marker type for the price table; kept as a plain dict for easy override."""


# Per-million-token prices (USD). ESTIMATES — override via config if billing differs.
# Keyed by model id. (input_per_mtok, output_per_mtok)
DEFAULT_PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (15.0, 75.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (0.80, 4.0),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Credentials (all optional at import; validated at point of use) ---
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
    exa_api_key: str = Field(default="", alias="EXA_API_KEY")
    github_token: str = Field(default="", alias="GITHUB_TOKEN")
    searxng_url: str = Field(default="", alias="SEARXNG_URL")

    # --- Models ---
    orchestrator_model: str = "claude-opus-4-8"
    subagent_model: str = "claude-sonnet-4-6"
    utility_model: str = "claude-haiku-4-5-20251001"

    # --- Runtime ---
    runs_dir: str = "runs"
    http_timeout_s: float = 30.0
    max_retries: int = 3

    def price_for(self, model: str) -> tuple[float, float]:
        return DEFAULT_PRICES.get(model, (0.0, 0.0))


def load_settings() -> Settings:
    return Settings()
