"""Check the duplicate groups and their review sheets (D011).

Inputs, for a given opposition: `processed/<opposition>/questions.json` and, in
`interim/<opposition>/`, `duplicates.json`, `dup_contexts.csv` and `dup_check.csv`.

This check is read-only. Errors block `opox make bank`: groups out of date with the
questions, invalid or contradictory decisions, and context pairs pending review.
Warnings are reviewed pairs of `dup_check.csv` not added yet. Pending rows of
`dup_check.csv` are optional and only reported.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from opox.extract.duplicates import (
    DupPaths,
    UnionFind,
    blocks_of,
    context_pairs,
    group_context,
    load_questions,
    make_groups,
    read_check_sheet,
    read_contexts_sheet,
    repeated_rows,
)
from opox.models.duplicates import DuplicateCollection, DuplicateGroup
from opox.models.questions import Question

log = logging.getLogger(__name__)

EXTRACT_HINT = "run `opox extract duplicates`"


@dataclass
class Resolution:
    questions: dict[str, Question] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    groups: list[list[str]] | None = None  # every answered question, split by context


def split_by_context(
    questions: dict[str, Question], blocks: list[list[str]], decisions: dict[tuple[str, str], str]
) -> tuple[list[list[str]], list[str]]:
    """Split the blocks whose crops are marked as different; also return contradictions.

    Crops joined by `y` are the same context. Questions without context stay with the
    most recent context of their block.
    """
    same = UnionFind()
    for (a, b), d in decisions.items():
        if d == "y":
            same.union(a, b)
    errors = [
        f"context pair marked n, but joined through other pairs: {a}, {b}"
        for (a, b), d in decisions.items()
        if d == "n" and same.find(a) == same.find(b)
    ]
    result: list[list[str]] = []
    for ids in blocks:
        qs = [questions[m] for m in ids]
        classes = {same.find(str(q.context)) for q in qs if q.context is not None}
        if len(classes) < 2:
            result.append(ids)
            continue
        top = same.find(str(group_context(qs)))
        by_class: dict[object, list[str]] = defaultdict(list)
        for q in qs:
            by_class[same.find(str(q.context)) if q.context else top].append(q.question_id)
        result += by_class.values()
    return result, errors


def resolve_duplicates(data_dir: Path, opposition: str) -> Resolution:
    """Validate the groups and sheets; if valid, also return the final groups."""
    paths = DupPaths.of(data_dir, opposition)
    res = Resolution()
    res.questions, res.errors = load_questions(paths.questions)
    if res.errors:
        return res
    for path in (paths.duplicates, paths.contexts_sheet, paths.check_sheet):
        if not path.is_file():
            res.errors.append(f"file not found: {path}; {EXTRACT_HINT}")
    if res.errors:
        return res
    try:
        collection = DuplicateCollection.model_validate_json(
            paths.duplicates.read_text(encoding="utf-8")
        )
    except ValidationError as e:
        res.errors.append(f"invalid model in {paths.duplicates}\n{e}")
        return res
    questions = res.questions

    # Groups: those of the file must be the exact ones joined by the manual ones.
    manual = [g.members for g in collection.groups if g.origin == "manual"]
    groups, unknown = make_groups(questions, manual)
    res.errors += [f"{paths.duplicates.name}: {u}" for u in unknown]
    if _as_set(groups) != _as_set(collection.groups):
        res.errors.append(
            f"{paths.duplicates} is out of date with {paths.questions}; {EXTRACT_HINT}"
        )
    log.info("%d group(s) in %s", len(collection.groups), paths.duplicates)

    # Contexts: every pair found in a group, decided once, without contradictions.
    rows, errors = read_contexts_sheet(paths.contexts_sheet)
    res.errors += errors + repeated_rows(rows, paths.contexts_sheet.name)
    pairs = context_pairs(questions, groups)
    sheet = paths.contexts_sheet.name
    res.errors += [
        f"{sheet} line {r.line}: pair not found in any group; {EXTRACT_HINT}"
        for r in rows
        if r.pair not in pairs
    ]
    in_sheet = {r.pair for r in rows}
    res.errors += [
        f"{sheet}: pair missing: {a}, {b}; {EXTRACT_HINT}"
        for a, b in pairs
        if (a, b) not in in_sheet
    ]
    pending = sum(1 for r in rows if r.pair in pairs and not r.same)
    if pending:
        res.errors.append(f"{pending} context pair(s) pending review in {paths.contexts_sheet}")
    decisions = {r.pair: r.same for r in rows if r.pair in pairs}

    # Possible duplicates: valid ids; reviewed pairs added; no `n` inside a group.
    check_rows, errors = read_check_sheet(paths.check_sheet)
    res.errors += errors + repeated_rows(check_rows, paths.check_sheet.name)
    blocks = blocks_of(questions, groups)
    block_of = {m: b for b, ids in enumerate(blocks) for m in ids}
    sheet = paths.check_sheet.name
    not_added = 0
    for r in check_rows:
        missing = [q for q in r.pair if q not in block_of]
        if missing:
            res.errors.append(
                f"{sheet} line {r.line}: question not answered or not found: {', '.join(missing)}"
            )
            continue
        joined = block_of[r.pair[0]] == block_of[r.pair[1]]
        if r.same == "n" and joined:
            res.errors.append(f"{sheet} line {r.line}: marked n, but both are in the same group")
        not_added += r.same == "y" and not joined
    if not_added:
        res.warnings.append(
            f"{not_added} reviewed pair(s) of {paths.check_sheet} not added; "
            "run `opox add duplicates`"
        )
    unreviewed = sum(not r.same for r in check_rows)
    if unreviewed:
        res.notes.append(f"{unreviewed} possible duplicate(s) not reviewed (optional)")

    final, errors = split_by_context(questions, blocks, decisions)
    res.errors += errors
    if not res.errors:
        res.groups = final
    return res


def _as_set(groups: list[DuplicateGroup]) -> set[tuple[tuple[str, ...], str]]:
    return {(tuple(g.members), g.origin) for g in groups}


def check_duplicates(data_dir: Path, opposition: str) -> tuple[list[str], list[str], list[str]]:
    """Return (errors, warnings, notes); errors empty if everything is complete and consistent."""
    res = resolve_duplicates(data_dir, opposition)
    if res.groups is not None:
        n_groups = sum(len(g) > 1 for g in res.groups)
        res.notes.append(
            f"{len(res.groups)} bank entr(ies) from {len(res.questions)} answered question(s), "
            f"{n_groups} with duplicates"
        )
    return res.errors, res.warnings, res.notes
