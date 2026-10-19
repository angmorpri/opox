"""Check the context control sheet against its crops and the extracted questions (D005).

Inputs, for a given opposition:
- `interim/<opposition>/contexts.csv`: control sheet, `exam_id, page, first, last`.
- `processed/<opposition>/contexts/`: one crop per sheet row.
- `processed/<opposition>/questions.json` and `rules.json`.
- `raw/<opposition>/tests/`: exam PDFs, to locate questions by page.

This check is read-only.
"""

import logging
from collections import defaultdict
from pathlib import Path, PurePosixPath

import pdfplumber
from pydantic import ValidationError

from opox.extract.contexts import (
    SHEET_COLUMNS,
    crop_name,
    locate_context,
    question_positions,
    read_sheet,
)
from opox.models.questions import ExamCollection
from opox.models.rules import CallRulesCollection

log = logging.getLogger(__name__)

PNG_SIGNATURE = bytes.fromhex("89504e470d0a1a0a")


def _parse_rows(rows: list[dict[str, str]]) -> tuple[list[tuple[str, int, int, int]], list[str]]:
    """Validate sheet rows; return (exam_id, page, first, last) tuples and errors."""
    parsed: list[tuple[str, int, int, int]] = []
    errors: list[str] = []
    seen: set[tuple[str, int]] = set()
    for i, row in enumerate(rows, start=2):  # line 1 is the header
        try:
            page, first, last = int(row["page"]), int(row["first"]), int(row["last"])
        except ValueError:
            errors.append(f"line {i}: page, first and last must be integers")
            continue
        exam_id = row["exam_id"]
        if min(page, first) < 1 or first > last:
            errors.append(f"line {i}: invalid values page={page}, first={first}, last={last}")
            continue
        if (exam_id, page) in seen:
            errors.append(f"line {i}: duplicate context {exam_id} p{page}")
            continue
        seen.add((exam_id, page))
        parsed.append((exam_id, page, first, last))
    return parsed, errors


def check_contexts(data_dir: Path, opposition: str) -> list[str]:
    """Return a list of problems found; empty if everything is consistent."""
    return resolve_contexts(data_dir, opposition)[0]


def resolve_contexts(data_dir: Path, opposition: str) -> tuple[list[str], dict[str, PurePosixPath]]:
    """Validate the sheet and crops; return (problems, context path of each question id).

    Paths are relative to `processed/<opposition>/`, as stored in `Question.context`.
    """
    sheet_path = data_dir / "interim" / opposition / "contexts.csv"
    processed_dir = data_dir / "processed" / opposition
    crops_dir = processed_dir / "contexts"
    questions_path = processed_dir / "questions.json"
    rules_path = processed_dir / "rules.json"
    tests_dir = data_dir / "raw" / opposition / "tests"

    for path in (sheet_path, questions_path, rules_path):
        if not path.is_file():
            return [f"file not found: {path}"], {}
    rows = read_sheet(sheet_path)
    if rows and list(rows[0]) != SHEET_COLUMNS:
        return [f"{sheet_path}: columns must be {', '.join(SHEET_COLUMNS)}"], {}
    try:
        exams = ExamCollection.model_validate_json(questions_path.read_text(encoding="utf-8"))
    except ValidationError as e:
        return [f"invalid model in {questions_path}\n{e}"], {}
    rules = CallRulesCollection.model_validate_json(rules_path.read_text(encoding="utf-8"))
    rules_by_id = {r.call_id: r for r in rules.root}
    question_ids = {q.question_id for e in exams.root for q in e.questions}

    contexts, errors = _parse_rows(rows)
    log.info("checking %d context(s) from %s", len(contexts), sheet_path)

    # Crops: one per row, and no crop without a row.
    expected_files = {crop_name(e, p) for e, p, _, _ in contexts}
    for name in sorted(expected_files):
        path = crops_dir / name
        if not path.is_file():
            errors.append(f"crop not found: {path}")
            continue
        with path.open("rb") as f:
            if f.read(len(PNG_SIGNATURE)) != PNG_SIGNATURE:
                errors.append(f"not a PNG image: {path}")
    for path in sorted(crops_dir.glob("*")):
        if path.name not in expected_files:
            errors.append(f"crop not in {sheet_path}: {path}")

    # Questions: each range must be found from its page on, and used by one context only.
    assignment: dict[str, PurePosixPath] = {}
    by_exam: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
    for exam_id, page, first, last in contexts:
        by_exam[exam_id].append((page, first, last))
    for i, (exam_id, exam_contexts) in enumerate(sorted(by_exam.items()), start=1):
        log.info("[%d/%d] %s", i, len(by_exam), exam_id)
        exam_pdf = tests_dir / f"{exam_id}T.pdf"
        call_rules = rules_by_id.get(exam_id[:5])
        if not exam_pdf.is_file():
            errors.append(f"{exam_id}: exam PDF not found: {exam_pdf}")
            continue
        if call_rules is None:
            errors.append(f"{exam_id}: call {exam_id[:5]} not found in {rules_path}")
            continue
        with pdfplumber.open(exam_pdf) as pdf:
            n_pages = len(pdf.pages)
        positions = question_positions(exam_pdf, call_rules)
        owner: dict[str, int] = {}
        for page, first, last in sorted(exam_contexts):
            where = f"{exam_id} p{page}"
            if page > n_pages:
                errors.append(f"{where}: exam has only {n_pages} pages")
                continue
            ids = locate_context(positions, page, first, last)
            if ids is None:
                errors.append(f"{where}: questions {first}-{last} not found from page {page} on")
                continue
            for qid in ids:
                if qid not in question_ids:
                    errors.append(f"{where}: {qid} missing in {questions_path}")
                if qid in owner:
                    errors.append(f"{where}: {qid} already used by {exam_id} p{owner[qid]}")
                owner[qid] = page
                assignment[qid] = PurePosixPath(crops_dir.name, crop_name(exam_id, page))

    return errors, assignment
