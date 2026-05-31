"""Write stage: synthesize the final report body from compressed findings.

The writer may use ONLY the provided findings and numbered sources, and must
cite with [n] markers. The authoritative Sources list is appended by the report
assembler (not the model) so source lines can't be fabricated.
"""

from __future__ import annotations

from research_agent.config import Settings
from research_agent.llm.base import LLMClient
from research_agent.models import Brief, Usage
from research_agent.pipeline.orchestrator import ResearchBundle

_SYSTEM = (
    "You are a research writer. Using ONLY the findings and numbered sources "
    "provided, write a thorough, well-organized report in Markdown that answers "
    "the objective. Requirements:\n"
    "- Start with an H1 title and a 2-4 sentence executive summary.\n"
    "- Add body sections (H2) covering the findings; synthesize across them, do "
    "not just concatenate.\n"
    "- Cite every factual claim with [n] markers matching the source numbers.\n"
    "- Do NOT invent sources, numbers, or facts not present in the findings.\n"
    "- Do NOT write a Sources/References section; it is appended automatically.\n"
    "- Be precise and dense; avoid filler."
)


async def write_report(
    client: LLMClient, settings: Settings, brief: Brief, bundle: ResearchBundle
) -> tuple[str, Usage]:
    sources = "\n".join(f"[{c.id}] {c.title} — {c.url}" for c in bundle.citations) or "(none)"
    findings = "\n\n".join(
        f"### {f.sub_question}\nCitations available: {[c.id for c in f.citations]}\n{f.summary}"
        for f in bundle.findings
    )
    user = (
        f"Objective: {brief.objective}\n"
        f"Scope notes: {brief.scope_notes or '(none)'}\n\n"
        f"NUMBERED SOURCES:\n{sources}\n\n"
        f"FINDINGS:\n{findings}"
    )
    resp = await client.complete(
        system=_SYSTEM,
        messages=[{"role": "user", "content": user}],
        model=settings.orchestrator_model,
        max_tokens=8192,
        tools=None,
    )
    return resp.text, resp.usage
