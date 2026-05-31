"""Run persistence: checkpoint each stage so a failed run can resume without
re-spending tokens, and write the final artifacts.

Only structured stage outputs and a decision/cost trace are persisted — never
raw source contents (see the logging policy in the design).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from research_agent.models import Report

T = TypeVar("T", bound=BaseModel)


def new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{uuid.uuid4().hex[:6]}"


class RunStore:
    """Filesystem-backed checkpoint store for one run."""

    def __init__(self, runs_dir: str, run_id: str) -> None:
        self.run_id = run_id
        self.dir = Path(runs_dir) / run_id
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, stage: str) -> Path:
        return self.dir / f"{stage}.json"

    def exists(self, stage: str) -> bool:
        return self._path(stage).exists()

    def save_json(self, stage: str, model: BaseModel) -> None:
        self._path(stage).write_text(model.model_dump_json(indent=2), encoding="utf-8")

    def load_json(self, stage: str, model_cls: type[T]) -> T | None:
        path = self._path(stage)
        if not path.exists():
            return None
        return model_cls.model_validate_json(path.read_text(encoding="utf-8"))

    def write_trace(self, trace: dict) -> None:
        self._path("trace").write_text(json.dumps(trace, indent=2, default=str), encoding="utf-8")

    def write_report(self, report: Report) -> Path:
        self.save_json("report", report)
        md_path = self.dir / "report.md"
        md_path.write_text(report.markdown, encoding="utf-8")
        return md_path
