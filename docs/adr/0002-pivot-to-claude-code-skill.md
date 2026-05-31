# ADR 0002: Retire the standalone app; ship as a Claude Code skill

**Date:** 2026-05-31
**Status:** Accepted (supersedes the delivery vehicle chosen in the design spec and ADR 0001)
**Decider:** user, after reviewing the trade-offs

## Context

v1 shipped as a standalone Python app on the Anthropic Messages API (ADR 0001).
The user then asked the right question: *why does this need to be a separate
program — can it just be a skill we use inside Claude Code, and what is the SDK
actually buying us?*

## What the standalone app was buying

Concretely, only four things the skill form can't do:

1. **Headless / scheduled / programmatic** execution (cron, API, calls from
   another app).
2. **Hard-coded enforcement** of the cost gate and citation-verification (vs.
   prompt-guided).
3. **CI tests + an eval harness.**
4. **Portability outside Claude Code.**

For the user's actual goal — invoking deep research *while working in Claude
Code* — none of those four matter, and the app's costs are real:

- Separate `ANTHROPIC_API_KEY` and **per-token billing** (the multi-agent fan-out
  is ~15x tokens). The skill runs on the existing Claude subscription.
- Re-implements search/orchestration that Claude Code already provides natively
  (WebSearch/WebFetch, the Bifrost MCP servers, and the Task sub-agent tool — the
  orchestrator-worker primitive).
- A whole Python package to maintain vs. one Markdown file.

The valuable IP was never the Python — it is the **playbook**
(Scope → Gauge → Research → Verify → Write, the complexity gate, citation
faithfulness). That ports directly into a skill.

## Decision

Retire the standalone Python app. Ship the methodology as a Claude Code skill,
`deep-research`, installed at `~/.claude/skills/deep-research/` with the
version-controlled source at `skills/deep-research/` in this repo.

The Python package, tests, and `pyproject.toml` are removed from the working tree
(preserved in git history through commit `3203ee2` and recoverable if a headless
service is ever needed — that would be the trigger to revive it).

## Consequences

- **Positive:** zero infra, no API billing, runs in-session on the subscription,
  reuses the full existing tool/MCP stack and native sub-agents, one-file
  maintenance, naturally invocable.
- **Negative:** no headless/scheduled/external-app use; cost gate and
  verification are now prompt-discipline rather than code-enforced; no CI eval
  harness. All acceptable for the interactive personal-use goal.
- **Reversal trigger:** if a headless research service or external-app
  integration becomes a real need, revive the app from git history — the
  architecture and ADR 0001 still hold.
