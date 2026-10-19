"""Check extracted exam questions against the call rules and the raw sources (D009).

Inputs, for a given opposition:
- `processed/<opposition>/questions.json`: extracted questions.
- `processed/<opposition>/rules.json`: expected parts and reserve lists of each call.
- `raw/<opposition>/tests/`: exam and answer key PDFs.
- `interim/<opposition>/contexts.csv` and `processed/<opposition>/contexts/` (D005).

This check is read-only. Errors are inconsistencies; warnings are pending steps.
"""

import logging
from pathlib import Path

from pydantic import ValidationError

from opox.extract.questions import expected_sections
from opox.models.questions import ExamCollection
from opox.models.rules import CallRulesCollection

log = logging.getLogger(__name__)


def check_questions(data_dir: Path, opposition: str) -> tuple[list[str], list[str]]:
    """Return (errors, warnings); both empty if everything is complete and consistent."""
    processed_dir = data_dir / "processed" / opposition
    questions_path = processed_dir / "questions.json"
    rules_path = processed_dir / "rules.json"
    raw_dir = data_dir / "raw" / opposition
    sheet_path = data_dir / "interim" / opposition / "contexts.csv"

    for path in (questions_path, rules_path):
        if not path.is_file():
            return [f"file not found: {path}"], []
    try:
        exams = ExamCollection.model_validate_json(questions_path.read_text(encoding="utf-8"))
    except ValidationError as e:
        return [f"invalid model in {questions_path}\n{e}"], []
    rules = CallRulesCollection.model_validate_json(rules_path.read_text(encoding="utf-8"))
    rules_by_id = {r.call_id: r for r in rules.root}

    errors: list[str] = []
    expected_ids = {p.stem[:-1] for p in (raw_dir / "tests").glob("*T.pdf")}
    exam_ids = {e.exam_id for e in exams.root}
    errors += [f"{i}: missing in {questions_path}" for i in sorted(expected_ids - exam_ids)]
    errors += [f"{i}: exam PDF not found" for i in sorted(exam_ids - expected_ids)]

    log.info("checking %d exam(s) from %s", len(exams.root), questions_path)
    for exam in exams.root:
        log.info("  %s: %d questions", exam.exam_id, len(exam.questions))
        for source in (exam.source, exam.key_source):
            if not (raw_dir / source).is_file():
                errors.append(f"{exam.exam_id}: source not found: {raw_dir / source}")
        call_rules = rules_by_id.get(exam.call_id)
        if call_rules is None:
            errors.append(f"{exam.exam_id}: call {exam.call_id} not found in {rules_path}")
            continue
        for section in expected_sections(call_rules):
            numbers = [
                q.number
                for q in exam.questions
                if q.part == section.part and q.is_reserve == section.is_reserve
            ]
            if numbers != list(range(1, section.size + 1)):
                label = f"part {section.part}{' reserve' if section.is_reserve else ''}"
                errors.append(
                    f"{exam.exam_id}: {label}: {len(numbers)} questions, expected 1..{section.size}"
                )
        for q in exam.questions:
            if q.context is not None and not (processed_dir / q.context).is_file():
                errors.append(f"{q.question_id}: context not found: {processed_dir / q.context}")

    warnings: list[str] = []
    has_contexts = any(q.context for e in exams.root for q in e.questions)
    if not sheet_path.is_file():
        warnings.append(f"contexts pending: {sheet_path} not found (D005)")
    elif not has_contexts:
        warnings.append("contexts pending: run `opox add contexts`")
    return errors, warnings
