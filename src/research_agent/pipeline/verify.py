"""Verify stage: the citation-faithfulness pass.

Fabricated or unsupported citations are the documented top failure mode of
research agents and they hide inside long reports. We extract every cited
sentence and check it against the actual text of its cited sources, flagging any
that aren't substantiated.
"""

from __future__ import annotations

import re

from research_agent.config import Settings
from research_agent.llm.agent import complete_json
from research_agent.llm.base import LLMClient
from research_agent.models import Claim, Usage

_MARKER_RE = re.compile(r"\[(\d+)\]")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_MAX_CLAIMS = 40  # cost guard; verify the first N cited sentences
_SOURCE_CHARS = 2000

_JUDGE_SYSTEM = (
    "You verify whether a CLAIM is supported by the provided SOURCE excerpts. "
    'Reply with ONLY JSON: {"supported": true|false, "note": "brief reason"}. '
    "Mark supported=true only if the sources substantiate the specific claim."
)


def extract_claims(markdown: str) -> list[Claim]:
    """Every sentence carrying a [n] citation marker becomes a verifiable claim."""
    claims: list[Claim] = []
    for sentence in _SENTENCE_SPLIT.split(markdown):
        text = sentence.strip()
        ids = sorted({int(m) for m in _MARKER_RE.findall(text)})
        if ids:
            claims.append(Claim(text=text, citation_ids=ids))
    return claims


async def verify_claims(
    client: LLMClient,
    settings: Settings,
    claims: list[Claim],
    source_text: dict[int, str],
) -> tuple[list[Claim], Usage]:
    usage = Usage()
    verified: list[Claim] = []
    for claim in claims[:_MAX_CLAIMS]:
        srcs = "\n\n".join(
            f"[{i}] {source_text.get(i, '(source text unavailable)')[:_SOURCE_CHARS]}"
            for i in claim.citation_ids
        )
        user = f"CLAIM: {claim.text}\n\nSOURCES:\n{srcs}"
        try:
            data, u = await complete_json(
                client, model=settings.utility_model, system=_JUDGE_SYSTEM, user=user, max_tokens=300
            )
            usage = usage.add(u)
            supported: bool | None = bool(data.get("supported", False))
            note = str(data.get("note", "")).strip()
        except Exception as exc:  # never let verification crash the run
            supported, note = None, f"verification error: {exc}"
        verified.append(claim.model_copy(update={"supported": supported, "verifier_note": note}))
    # claims beyond the cap pass through unverified
    verified.extend(claims[_MAX_CLAIMS:])
    return verified, usage


def unsupported(claims: list[Claim]) -> list[Claim]:
    return [c for c in claims if c.supported is False]
