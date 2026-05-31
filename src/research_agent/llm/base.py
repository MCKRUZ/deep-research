"""LLM transport abstraction.

The whole system talks to models through ``LLMClient`` so the orchestration loop
stays deterministic and testable. Production uses ``AnthropicClient``; tests use
``FakeLLMClient``. See ADR 0001 for why we own this seam.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol

from research_agent.models import Usage

# An LLM message in Anthropic wire format: {"role": "user"|"assistant", "content": ...}
Message = dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    """A model's request to invoke a tool."""

    id: str
    name: str
    input: dict[str, Any]


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"
    usage: Usage = field(default_factory=Usage)


@dataclass
class ToolSpec:
    """A tool exposed to a model, with the handler that executes it.

    ``handler`` receives the tool input dict and returns a text result that is
    fed back to the model as a tool_result block.
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Awaitable[str]]

    def wire(self) -> dict[str, Any]:
        """Anthropic tools-API representation (no handler)."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class LLMClient(Protocol):
    async def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        model: str,
        max_tokens: int,
        tools: list[ToolSpec] | None = None,
        temperature: float = 0.0,
    ) -> LLMResponse: ...
