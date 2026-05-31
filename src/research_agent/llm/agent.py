"""The agent loop: the one place we own the tool-use cycle.

``run_agent`` drives a bounded reason -> act -> observe loop against any
``LLMClient``. ``complete_json`` is a structured-output helper for stages that
need a parsed object (classifier, brief, verifier, judge).

Budget discipline lives here: tool calls are hard-capped, and when the cap is
hit the model is told to stop and synthesize rather than being allowed to spin.
Tool exceptions are surfaced to the model as text (it adapts) instead of
crashing the run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from research_agent.llm.base import LLMClient, Message, ToolSpec
from research_agent.models import Usage


@dataclass
class AgentResult:
    text: str
    usage: Usage = field(default_factory=Usage)
    tool_calls_made: int = 0
    transcript: list[Message] = field(default_factory=list)


def _result_block(tool_use_id: str, content: str, *, is_error: bool = False) -> dict[str, Any]:
    block: dict[str, Any] = {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content,
    }
    if is_error:
        block["is_error"] = True
    return block


async def run_agent(
    *,
    client: LLMClient,
    model: str,
    system: str,
    user: str,
    tools: list[ToolSpec],
    max_tool_calls: int,
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> AgentResult:
    tool_map = {t.name: t for t in tools}
    messages: list[Message] = [{"role": "user", "content": user}]
    total = Usage()
    calls = 0

    while True:
        resp = await client.complete(
            system=system,
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            tools=tools or None,
            temperature=temperature,
        )
        total = total.add(resp.usage)

        assistant_content: list[dict[str, Any]] = []
        if resp.text:
            assistant_content.append({"type": "text", "text": resp.text})
        for tc in resp.tool_calls:
            assistant_content.append(
                {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.input}
            )
        messages.append({"role": "assistant", "content": assistant_content or resp.text})

        if not resp.tool_calls:
            return AgentResult(resp.text, total, calls, messages)

        results: list[dict[str, Any]] = []
        for tc in resp.tool_calls:
            if calls >= max_tool_calls:
                results.append(
                    _result_block(
                        tc.id,
                        "Tool-call budget exhausted. Stop searching and write your "
                        "final answer from the evidence already gathered.",
                    )
                )
                continue
            calls += 1
            spec = tool_map.get(tc.name)
            if spec is None:
                results.append(_result_block(tc.id, f"Unknown tool: {tc.name}", is_error=True))
                continue
            try:
                out = await spec.handler(tc.input)
            except Exception as exc:  # surface to the model, do not crash the run
                out = f"Tool '{tc.name}' failed: {exc}. Try a different query or tool."
            results.append(_result_block(tc.id, out))

        budget_hit = calls >= max_tool_calls
        if budget_hit:
            # Fold the stop instruction into the SAME user turn as the tool
            # results — appending a second user message would break the
            # assistant/user alternation the API requires.
            results.append(
                {
                    "type": "text",
                    "text": "Budget reached. Provide your final answer now from the "
                    "evidence gathered.",
                }
            )
        messages.append({"role": "user", "content": results})

        if budget_hit:
            final = await client.complete(
                system=system,
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                tools=None,
                temperature=temperature,
            )
            total = total.add(final.usage)
            messages.append({"role": "assistant", "content": final.text})
            return AgentResult(final.text, total, calls, messages)


def extract_json(text: str) -> Any | None:
    """Best-effort JSON extraction tolerant of code fences and surrounding prose."""
    text = text.strip()
    if text.startswith("```"):
        # strip a ```json ... ``` fence
        inner = text.split("```", 2)
        if len(inner) >= 2:
            body = inner[1]
            body = body[4:] if body.lstrip().startswith("json") else body
            text = body.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


async def complete_json(
    client: LLMClient,
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 2048,
    retries: int = 2,
) -> tuple[Any, Usage]:
    messages: list[Message] = [{"role": "user", "content": user}]
    usage = Usage()
    for _ in range(retries + 1):
        resp = await client.complete(
            system=system, messages=messages, model=model, max_tokens=max_tokens, tools=None
        )
        usage = usage.add(resp.usage)
        data = extract_json(resp.text)
        if data is not None:
            return data, usage
        messages.append({"role": "assistant", "content": resp.text})
        messages.append(
            {"role": "user", "content": "That was not valid JSON. Reply with ONLY one JSON object."}
        )
    raise ValueError("Model did not return valid JSON")
