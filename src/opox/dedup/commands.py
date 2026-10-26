"""`opox dedup extract | add | check` for the answers and stems stages (D011).

Inputs, for a given opposition: `processed/<opposition>/questions.json` and, in `stems`,
`interim/<opposition>/dedup_answers.json`.

Outputs, in `interim/<opposition>/`, per stage `<s>`:
- `dedup_<s>.json`: groups (`DedupCollection`), derived from the inputs and the sheet.
- `dedup_<s>_review.csv`: review sheet, the only source of manual decisions.
- `dedup_<s>_review.md`: review guide, always regenerated with the sheet.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from opox.dedup.core import (
    STAGES,
    Case,
    Member,
    Resolution,
    Stage,
    answer_blocks,
    answered,
    build_members,
    find_cases,
    resolve,
)
from opox.dedup.review import read_sheet, sheet_rows, write_guide, write_sheet
from opox.models.dedup import DedupCollection
from opox.models.questions import ExamCollection

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DedupPaths:
    questions: Path
    answers: Path  # dedup_answers.json, input of `stems`
    stems: Path  # dedup_stems.json, input of `contexts`
    json: Path
    sheet: Path
    guide: Path

    @classmethod
    def of(cls, data_dir: Path, opposition: str, stage: str) -> DedupPaths:
        interim = data_dir / "interim" / opposition
        return cls(
            questions=data_dir / "processed" / opposition / "questions.json",
            answers=interim / "dedup_answers.json",
            stems=interim / "dedup_stems.json",
            json=interim / f"dedup_{stage}.json",
            sheet=interim / f"dedup_{stage}_review.csv",
            guide=interim / f"dedup_{stage}_review.md",
        )


@dataclass(frozen=True)
class Inputs:
    members: list[Member]
    cases: list[Case]
    question_ids: set[str]  # answered questions
    blocks: dict[str, int]  # answer block of each question


def read_collection(path: Path) -> tuple[DedupCollection | None, str | None]:
    if not path.is_file():
        return None, f"file not found: {path}"
    try:
        return DedupCollection.model_validate_json(path.read_text(encoding="utf-8")), None
    except ValidationError as e:
        return None, f"invalid model in {path}\n{e}"


def load_inputs(paths: DedupPaths, stage: Stage) -> tuple[Inputs | None, list[str]]:
    """Members and cases of the stage, or the errors that prevent computing them."""
    if not paths.questions.is_file():
        return None, [f"file not found: {paths.questions}"]
    exams = ExamCollection.model_validate_json(paths.questions.read_text(encoding="utf-8"))
    questions = answered(exams)
    ids = {q.question_id for q in questions}
    blocks = [questions]
    if stage.name == "stems":
        answers, error = read_collection(paths.answers)
        if error:
            return None, [error, "run the answers stage first"]
        assert answers is not None
        if {s for g in answers.root for s in g.sources} != ids:
            return None, [
                f"{paths.answers} does not cover the answered questions of {paths.questions}",
                "repeat the answers stage (`opox dedup check answers`)",
            ]
        blocks = answer_blocks(questions, answers)
    log.info("%d answered question(s) in %d block(s)", len(questions), len(blocks))
    members = build_members(blocks, stage)
    cases = find_cases(members, stage)
    by_block = {q.question_id: b for b, block in enumerate(blocks) for q in block}
    return Inputs(members, cases, ids, by_block), []


def write_collection(path: Path, collection: DedupCollection) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(collection.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _summary(res: Resolution, stage: Stage, paths: DedupPaths) -> list[str]:
    """Warnings about the sheet that `add` tolerates."""
    notes = [f"WARNING {paths.sheet.name} {s}" for s in res.stale]
    notes += [f"WARNING member missing from {paths.sheet.name}: {m}" for m in res.missing]
    if res.stale or res.missing:
        notes.append(f"regenerate the sheet with `opox dedup extract {stage.name} --force`")
    if res.pending:
        notes.append(f"{res.pending} member(s) pending review in {paths.sheet}")
    return notes


def extract(
    data_dir: Path, opposition: str, stage_name: str, force: bool = False
) -> tuple[bool, list[str]]:
    """Write the sheet, the guide and the groups of a stage. Return (success, notes)."""
    stage = STAGES[stage_name]
    paths = DedupPaths.of(data_dir, opposition, stage.name)
    inputs, errors = load_inputs(paths, stage)
    if errors:
        return False, errors
    assert inputs is not None

    existing = [p for p in (paths.json, paths.sheet) if p.exists()]
    if existing and not force:
        return False, [f"{p} already exists" for p in existing] + [
            "use --force to regenerate them, keeping the decisions of existing members"
        ]
    labels: dict[str, str] = {}
    if paths.sheet.exists():
        old_rows, errors = read_sheet(paths.sheet)
        if errors:
            return False, [*errors, "fix or remove the sheet and retry"]
        labels = {r.questions: r.group for r in old_rows if r.group}

    rows = sheet_rows(inputs.cases, stage, labels)
    kept = {r[4] for r in rows} & set(labels)
    notes = [f"overwriting {p}" for p in existing]
    notes += [f"decision lost: {ids} (group {labels[ids]!r})" for ids in labels if ids not in kept]
    write_sheet(paths.sheet, rows)
    write_guide(paths.guide, opposition, stage, inputs.cases)
    notes.append(
        f"{len(inputs.cases)} case(s), {len(rows)} member(s), {len(kept)} decision(s) kept "
        f"-> {paths.sheet}, {paths.guide}"
    )

    res = resolve(inputs.members, inputs.cases, read_sheet(paths.sheet)[0])
    if res.errors:
        return False, [*notes, *res.errors, f"fix the sheet and run `opox dedup add {stage.name}`"]
    assert res.collection is not None
    write_collection(paths.json, res.collection)
    notes.append(f"{len(res.collection.root)} group(s) written to {paths.json}")
    notes += _summary(res, stage, paths)
    return True, notes


def add(data_dir: Path, opposition: str, stage_name: str) -> tuple[bool, list[str]]:
    """Rebuild the groups of a stage from the sheet. Return (success, notes)."""
    stage = STAGES[stage_name]
    paths = DedupPaths.of(data_dir, opposition, stage.name)
    inputs, errors = load_inputs(paths, stage)
    if errors:
        return False, errors
    assert inputs is not None
    if not paths.sheet.is_file():
        return False, [f"file not found: {paths.sheet}", f"run `opox dedup extract {stage.name}`"]
    rows, errors = read_sheet(paths.sheet)
    if errors:
        return False, errors

    res = resolve(inputs.members, inputs.cases, rows)
    if res.errors:
        return False, [*res.errors, "fix the sheet and retry"]
    assert res.collection is not None
    current, _ = read_collection(paths.json)
    if current == res.collection:
        notes = [f"{paths.json} already up to date"]
    else:
        write_collection(paths.json, res.collection)
        notes = [f"{len(res.collection.root)} group(s) written to {paths.json}"]
    if stage.name == "answers":
        notes.append("if the groups changed, repeat the stems stage")
    return True, notes + _summary(res, stage, paths)


def check(data_dir: Path, opposition: str, stage_name: str) -> list[str]:
    """Return the problems of a stage; empty if it is complete and consistent. Read-only."""
    stage = STAGES[stage_name]
    paths = DedupPaths.of(data_dir, opposition, stage.name)
    inputs, errors = load_inputs(paths, stage)
    if errors:
        return errors
    assert inputs is not None
    collection, error = read_collection(paths.json)
    if error:
        return [error]
    assert collection is not None

    sources = [s for g in collection.root for s in g.sources]
    errors += [
        f"answered question not in any group: {q}" for q in inputs.question_ids - set(sources)
    ]
    errors += [
        f"unknown or unanswered question in a group: {q}"
        for q in set(sources) - inputs.question_ids
    ]
    for g in collection.root:
        if len({inputs.blocks.get(s) for s in g.sources}) > 1:
            errors.append(f"group {g.canonical} spans several answer groups")

    if not paths.sheet.is_file():
        return [*errors, f"file not found: {paths.sheet}"]
    rows, sheet_errors = read_sheet(paths.sheet)
    if sheet_errors:
        return errors + sheet_errors
    res = resolve(inputs.members, inputs.cases, rows)
    errors += res.errors
    errors += [f"{paths.sheet.name} {s}" for s in res.stale]
    errors += [f"member missing from {paths.sheet.name}: {m}" for m in res.missing]
    if res.pending:
        errors.append(f"{res.pending} member(s) pending review in {paths.sheet}")
    if res.collection is not None and res.collection != collection:
        errors.append(f"{paths.json} differs from the sheet; run `opox dedup add {stage.name}`")
    return errors
