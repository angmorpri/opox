"""The chained deduplication stages, in order (D011)."""

from pathlib import Path
from types import ModuleType

from opox.dedup import commands, contexts

STAGE_ORDER = ("answers", "stems", "contexts")


def stage_module(stage: str) -> ModuleType:
    """Module implementing `extract`, `add` and `check` for a stage."""
    return contexts if stage == "contexts" else commands


def check_all(data_dir: Path, opposition: str) -> dict[str, list[str]]:
    """Problems of every stage, in order; empty lists if all are complete."""
    return {s: stage_module(s).check(data_dir, opposition, s) for s in STAGE_ORDER}


def started(data_dir: Path, opposition: str) -> bool:
    """Whether any stage has written its groups."""
    return any(commands.DedupPaths.of(data_dir, opposition, s).json.exists() for s in STAGE_ORDER)
