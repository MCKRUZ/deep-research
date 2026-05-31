"""Deterministic in-memory LLMClient for tests. No network.

Two ways to script it:
- ``responses``: a queue of LLMResponse returned in call order.
- ``router``: a callable (system, messages, model, tools) -> LLMResponse | None;
  return None to fall through to the queue.
"""

from __future__ import annotations

from typing import Any, Callable

from research_agent.llm.base import LLMResponse, Message, ToolCall, ToolSpec
from research_agent.models import Usage

Router = Callable[[str, list[Message], str, "list[ToolSpec] | None"], "LLMResponse | None"]


class FakeLLMClient:
    def __init__(
        self,
        responses: list[LLMResponse] | None = None,
        router: Router | None = None,
    ) -> None:
        self._queue = list(responses or [])
        self._router = router
        self.calls: list[dict[str, Any]] = []

    async def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        model: str,
        max_tokens: int,
        tools: list[ToolSpec] | None = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        self.calls.append(
            {"system": system, "messages": messages, "model": model, "tools": tools}
        )
        if self._router is not None:
            routed = self._router(system, messages, model, tools)
            if routed is not None:
                return routed
        if self._queue:
            return self._queue.pop(0)
        return LLMResponse(text="", stop_reason="end_turn", usage=Usage())


def text_response(text: str, *, in_tok: int = 10, out_tok: int = 10) -> LLMResponse:
    return LLMResponse(
        text=text,
        stop_reason="end_turn",
        usage=Usage(input_tokens=in_tok, output_tokens=out_tok),
    )


def tool_response(
    name: str, tool_input: dict[str, Any], *, call_id: str = "t1", in_tok: int = 10, out_tok: int = 10
) -> LLMResponse:
    return LLMResponse(
        text="",
        tool_calls=[ToolCall(id=call_id, name=name, input=tool_input)],
        stop_reason="tool_use",
        usage=Usage(input_tokens=in_tok, output_tokens=out_tok),
    )
