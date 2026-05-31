# ADR 0001: Own the orchestration on the Anthropic Messages API

**Date:** 2026-05-31
**Status:** Accepted
**Decider:** autonomous build (delegated decision authority)

## Context

The design (`docs/superpowers/specs/2026-05-31-research-agent-design.md`) chose to
"start native with `claude-agent-sdk` (approach A), escalate to a thin custom
orchestrator (approach C) only if the SDK cannot enforce the complexity gate
cleanly." The single open verification item was the exact `claude-agent-sdk`
subagent / parallel-tool API.

## Verification (what we found)

Confirmed via Context7 against `/anthropics/claude-agent-sdk-python`:

- The SDK is **the engine behind the Claude Code CLI** and operates by
  subprocessing that CLI (`ClaudeSDKClient` drives "interactive conversations
  with Claude Code"). Custom tools run in-process via `@tool` +
  `create_sdk_mcp_server`, but the **agent loop, sub-agent spawning, and parallel
  scheduling are owned by the CLI engine, not the caller.**
- Consequences for this project:
  1. The **cost-gated parallel fan-out** — the differentiating feature of this
     design — could not be directly controlled by our code.
  2. The system would be coupled to a CLI subprocess that is hard to exercise
     deterministically in unit tests, jeopardizing the "green tests" bar.
  3. Execution would require the `claude` CLI installed and authenticated.

## Decision

Build the orchestration ourselves on the **`anthropic` Python SDK (Messages
API)**, behind an `LLMClient` protocol (`research_agent.llm.base.LLMClient`).

- The agent loop, tool-use loop, complexity gate, and parallel sub-agent
  scheduling are our code — fully controllable and testable.
- `AnthropicClient` is the production `LLMClient`; `FakeLLMClient` (scripted
  responses) powers deterministic tests with zero network calls.
- A transport seam is preserved: a future `ClaudeAgentSDKClient` adapter can
  implement `LLMClient` for anyone who wants subscription/CLI-native execution.

This is the agreed A→C escalation, taken one step further to B because
verification showed approach C (sub-agents via the SDK) inherits the same CLI
coupling and the same loss of cost-gate control.

## Consequences

- **Positive:** deterministic tests, full cost-gate control, standard well-known
  API surface, model-agnostic via config, no CLI dependency.
- **Negative:** we own the tool-use loop, retries, and state (more code than
  leaning on the SDK). Mitigated by keeping the loop small, well-tested, and in
  one module (`research_agent.llm.agent`).
- **Cost note:** uses per-token API billing (requires `ANTHROPIC_API_KEY`), not a
  Claude subscription. The `LLMClient` seam leaves the subscription path open.
