"""Assign context crops to the extracted questions (D005).

Inputs, for a given opposition: the control sheet and crops, validated as in
`opox check contexts`, and `processed/<opposition>/questions.json`.

Output: `questions.json`, with `context` set from the sheet and cleared elsewhere. The
sheet is the source of truth, so previous assignments are always replaced.
"""

import logging
from pathlib import Path, PurePosixPath

from opox.checks.contexts import resolve_contexts
from opox.models.questions import ExamCollection

log = logging.getLogger(__name__)


def assign_contexts(exams: ExamCollection, assignment: dict[str, PurePosixPath]) -> ExamCollection:
    """Set each question's context from the assignment, clearing the rest."""
    return ExamCollection(
        [
            exam.model_copy(
                update={
                    "questions": [
                        q.model_copy(update={"context": assignment.get(q.question_id)})
                        for q in exam.questions
                    ]
                }
            )
            for exam in exams.root
        ]
    )


def add_contexts(data_dir: Path, opposition: str) -> tuple[bool, list[str]]:
    """Assign contexts to questions. Return (success, notes)."""
    errors, assignment = resolve_contexts(data_dir, opposition)
    if errors:
        return False, [*errors, "fix the problems above (`opox check contexts`) and retry"]

    questions_path = data_dir / "processed" / opposition / "questions.json"
    exams = ExamCollection.model_validate_json(questions_path.read_text(encoding="utf-8"))
    new_exams = assign_contexts(exams, assignment)
    questions_path.write_text(new_exams.model_dump_json(indent=2) + "\n", encoding="utf-8")
    n_with_context = sum(q.context is not None for e in new_exams.root for q in e.questions)
    log.info("contexts written to %s", questions_path)
    return True, [f"{n_with_context} question(s) with context in {questions_path}"]
