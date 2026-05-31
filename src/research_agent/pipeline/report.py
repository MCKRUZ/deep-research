"""Assemble the final Markdown report: writer body + verification summary +
authoritative Sources list (built from data, never from the model)."""

from __future__ import annotations

from research_agent.models import Brief, Citation, Claim, ComplexityTier, Report, Usage
from research_agent.pipeline.verify import unsupported


def assemble_markdown(body: str, citations: list[Citation], claims: list[Claim]) -> str:
    parts: list[str] = [body.strip()]

    checked = [c for c in claims if c.supported is not None]
    supported = [c for c in checked if c.supported is True]
    flagged = unsupported(claims)

    ver: list[str] = [
        "## Verification",
        f"- Cited claims checked: {len(checked)}",
        f"- Supported by sources: {len(supported)}",
        f"- Flagged as unsupported: {len(flagged)}",
    ]
    if flagged:
        ver.append("")
        ver.append("**Flagged claims** (cited sources did not substantiate these):")
        for c in flagged:
            ver.append(f"- {c.text} (cited {c.citation_ids}) — {c.verifier_note}")
    parts.append("\n".join(ver))

    src: list[str] = ["## Sources"]
    for c in citations:
        src.append(f"{c.id}. [{c.title}]({c.url}) — {c.source_type.value}")
    if not citations:
        src.append("_No sources were retrieved._")
    parts.append("\n".join(src))

    return "\n\n".join(parts) + "\n"


def build_report(
    *,
    brief: Brief,
    body: str,
    citations: list[Citation],
    claims: list[Claim],
    tier: ComplexityTier,
    usage: Usage,
) -> Report:
    return Report(
        query=brief.query,
        brief=brief,
        markdown=assemble_markdown(body, citations, claims),
        citations=citations,
        claims=claims,
        tier=tier,
        usage=usage,
    )
