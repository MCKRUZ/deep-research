"""Production LLMClient backed by the Anthropic Messages API."""

from __future__ import annotations

import asyncio

from research_agent.config import Settings
from research_agent.llm.base import LLMResponse, Message, ToolCall, ToolSpec
from research_agent.models import Usage


class AnthropicClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to your environment or .env file."
            )
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._settings = settings

    def _cost(self, model: str, usage: object) -> Usage:
        in_tok = getattr(usage, "input_tokens", 0)
        out_tok = getattr(usage, "output_tokens", 0)
        p_in, p_out = self._settings.price_for(model)
        cost = (in_tok / 1_000_000) * p_in + (out_tok / 1_000_000) * p_out
        return Usage(input_tokens=in_tok, output_tokens=out_tok, cost_usd=round(cost, 6))

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
        from anthropic import APIConnectionError, APIStatusError, RateLimitError

        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = [t.wire() for t in tools]

        last_exc: Exception | None = None
        for attempt in range(self._settings.max_retries):
            try:
                resp = await self._client.messages.create(**kwargs)
                break
            except (RateLimitError, APIConnectionError) as exc:
                last_exc = exc
                await asyncio.sleep(min(2**attempt, 8))
            except APIStatusError as exc:
                if exc.status_code and 500 <= exc.status_code < 600:
                    last_exc = exc
                    await asyncio.sleep(min(2**attempt, 8))
                    continue
                raise
        else:
            raise RuntimeError(f"Anthropic request failed after retries: {last_exc}")

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, input=dict(block.input)))

        return LLMResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=resp.stop_reason or "end_turn",
            usage=self._cost(model, resp.usage),
        )
