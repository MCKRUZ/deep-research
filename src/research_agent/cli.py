"""Command-line interface.

``research "<query>"`` runs the pipeline; ``research-eval`` runs the eval harness.
Both are thin wrappers: they wire config + client + registry and delegate to the
pipeline. The CLI owns the one interactive moment — clarifying questions —
unless ``--yes`` or a non-interactive stdin.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt

from research_agent.config import Settings, load_settings
from research_agent.models import Clarification, EffortLevel, Report
from research_agent.pipeline.run import run_pipeline
from research_agent.pipeline.scope import build_brief, generate_questions
from research_agent.state import RunStore, new_run_id

console = Console()


def _make_client(settings: Settings):
    from research_agent.llm.anthropic_client import AnthropicClient

    return AnthropicClient(settings)


async def _collect_clarifications(
    client, settings: Settings, query: str, interactive: bool
) -> tuple[list[Clarification], object]:
    from research_agent.models import Usage

    if not interactive:
        return [], Usage()
    questions, usage = await generate_questions(client, settings, query)
    clarifications: list[Clarification] = []
    for q in questions:
        answer = Prompt.ask(f"[cyan]?[/cyan] {q}", default="(no preference)")
        clarifications.append(Clarification(question=q, answer=answer))
    return clarifications, usage


async def _run(query: str, effort: EffortLevel, yes: bool, out: Optional[Path]) -> None:
    settings = load_settings()
    try:
        client = _make_client(settings)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2)

    from research_agent.tools.factory import build_registry

    registry = build_registry(settings)

    interactive = (not yes) and sys.stdin.isatty()
    clarifications, scope_usage = await _collect_clarifications(client, settings, query, interactive)

    with console.status("[bold]Scoping…[/bold]"):
        brief, bu = await build_brief(client, settings, query, clarifications)
    scope_usage = scope_usage.add(bu)
    console.print(f"[dim]Objective:[/dim] {brief.objective}")
    console.print(f"[dim]Sub-questions ({len(brief.sub_questions)}):[/dim] {brief.sub_questions}")

    store = RunStore(settings.runs_dir, new_run_id())
    with console.status("[bold]Researching, verifying, writing…[/bold]"):
        report = await run_pipeline(
            client, settings, brief, registry, effort=effort, store=store, seed_usage=scope_usage
        )

    _print_summary(report, store)
    if out is not None:
        out.write_text(report.markdown, encoding="utf-8")
        console.print(f"[green]Report written to[/green] {out}")


def _print_summary(report: Report, store: RunStore) -> None:
    flagged = len([c for c in report.claims if c.supported is False])
    checked = len([c for c in report.claims if c.supported is not None])
    console.rule("[bold green]Done[/bold green]")
    console.print(f"Tier: [bold]{report.tier.value}[/bold]")
    console.print(f"Sources: [bold]{len(report.citations)}[/bold]")
    console.print(f"Claims verified: [bold]{checked}[/bold]  Flagged: [bold]{flagged}[/bold]")
    console.print(
        f"Cost: [bold]${report.usage.cost_usd:.4f}[/bold] "
        f"({report.usage.input_tokens} in / {report.usage.output_tokens} out)"
    )
    console.print(f"Artifacts: [bold]{store.dir}[/bold]  (report.md, report.json, trace.json)")


def _research_cmd(
    query: str = typer.Argument(..., help="The research question."),
    effort: EffortLevel = typer.Option(EffortLevel.medium, help="Budget knob."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip clarifying questions."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Also write report.md here."),
) -> None:
    """Research a question and produce a citation-verified Markdown report."""
    asyncio.run(_run(query, effort, yes, out))


def _eval_cmd(
    effort: EffortLevel = typer.Option(EffortLevel.medium, help="Budget knob."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Write eval summary JSON here."),
) -> None:
    """Run the LLM-as-judge eval harness over the seed queries."""

    async def _go() -> None:
        settings = load_settings()
        try:
            client = _make_client(settings)
        except RuntimeError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=2)
        from research_agent.eval.harness import run_eval
        from research_agent.tools.factory import build_registry

        registry = build_registry(settings)
        with console.status("[bold]Running eval…[/bold]"):
            summary = await run_eval(client, settings, registry, effort=effort)
        console.rule("[bold]Eval summary[/bold]")
        for c in summary.cases:
            console.print(f"{c.id:18} {c.tier:8} overall={c.overall}  flagged={c.flagged_claims}")
        console.print(
            f"\n[bold]Means[/bold] overall={summary.mean_overall} "
            f"factual={summary.mean_factual} citation={summary.mean_citation} "
            f"completeness={summary.mean_completeness} source={summary.mean_source_quality}"
        )
        console.print(f"[bold]Total cost[/bold] ${summary.total_usage.cost_usd:.4f}")
        if out is not None:
            out.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
            console.print(f"[green]Summary written to[/green] {out}")

    asyncio.run(_go())


def app() -> None:
    typer.run(_research_cmd)


def eval_app() -> None:
    typer.run(_eval_cmd)
