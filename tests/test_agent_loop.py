from __future__ import annotations

import pytest

from research_agent.llm.agent import complete_json, extract_json, run_agent
from research_agent.llm.base import ToolSpec
from research_agent.llm.fake import FakeLLMClient, text_response, tool_response


def _echo_tool(recorder: list[str]) -> ToolSpec:
    async def handler(args: dict) -> str:
        recorder.append(args.get("query", ""))
        return "tool output"

    return ToolSpec(
        name="echo",
        description="echo",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        handler=handler,
    )


async def test_run_agent_executes_tool_then_returns_text():
    recorder: list[str] = []
    client = FakeLLMClient(
        responses=[tool_response("echo", {"query": "hi"}), text_response("final answer")]
    )
    result = await run_agent(
        client=client, model="m", system="sys", user="go",
        tools=[_echo_tool(recorder)], max_tool_calls=5,
    )
    assert result.text == "final answer"
    assert result.tool_calls_made == 1
    assert recorder == ["hi"]


async def test_run_agent_enforces_tool_budget():
    recorder: list[str] = []
    # Model always wants to call the tool; budget must stop it.
    client = FakeLLMClient(router=lambda *a: tool_response("echo", {"query": "again"}))
    result = await run_agent(
        client=client, model="m", system="sys", user="go",
        tools=[_echo_tool(recorder)], max_tool_calls=2,
    )
    assert result.tool_calls_made == 2  # never exceeds the cap


async def test_run_agent_surfaces_tool_error_without_crashing():
    async def boom(args: dict) -> str:
        raise ValueError("kaboom")

    tool = ToolSpec(name="echo", description="d", input_schema={"type": "object"}, handler=boom)
    client = FakeLLMClient(
        responses=[tool_response("echo", {"query": "x"}), text_response("recovered")]
    )
    result = await run_agent(
        client=client, model="m", system="s", user="u", tools=[tool], max_tool_calls=3
    )
    assert result.text == "recovered"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ('{"a": 1}', {"a": 1}),
        ('```json\n{"a": 2}\n```', {"a": 2}),
        ('prefix {"a": 3} suffix', {"a": 3}),
        ("not json", None),
    ],
)
def test_extract_json(raw, expected):
    assert extract_json(raw) == expected


async def test_complete_json_retries_then_parses():
    client = FakeLLMClient(responses=[text_response("garbage"), text_response('{"ok": true}')])
    data, usage = await complete_json(client, model="m", system="s", user="u")
    assert data == {"ok": True}
    assert usage.output_tokens > 0
