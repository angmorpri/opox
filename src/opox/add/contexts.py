"""Assign context crops to the extracted questions (D005).

Inputs, for a given opposition: the control sheet and crops, validated as in
`opox check contexts`, and `processed/<opposition>/questions.json`.

Output: `questions.json`, with `context` set from the sheet and cleared elsewhere. Adding
a context is always allowed; replacing or clearing an existing one requires `force` (D006).
"""

import logging
from pathlib import Path, PurePosixPath

from opox.checks.contexts import resolve_contexts
from opox.models.questions import Exam, ExamCollection

log = logging.getLogger(__name__)


def assign_contexts(
    exams: ExamCollection, assignment: dict[str, PurePosixPath]
) -> tuple[ExamCollection, list[str], list[str]]:
    """Apply an assignment; return (new collection, added ids, replaced or cleared notes)."""
    added: list[str] = []
    changed: list[str] = []
    new_exams: list[Exam] = []
    for exam in exams.root:
        questions = []
        for q in exam.questions:
            context = assignment.get(q.question_id)
            if context != q.context:
                if q.context is None:
                    added.append(q.question_id)
                else:
                    changed.append(f"{q.question_id}: {q.context} -> {context}")
                q = q.model_copy(update={"context": context})
            questions.append(q)
        new_exams.append(exam.model_copy(update={"questions": questions}))
    return ExamCollection(new_exams), added, changed


def add_contexts(data_dir: Path, opposition: str, force: bool = False) -> tuple[bool, list[str]]:
    """Assign contexts to questions. Return (success, notes)."""
    errors, assignment = resolve_contexts(data_dir, opposition)
    if errors:
        return False, [*errors, "fix the problems above (`opox check contexts`) and retry"]

    questions_path = data_dir / "processed" / opposition / "questions.json"
    exams = ExamCollection.model_validate_json(questions_path.read_text(encoding="utf-8"))
    new_exams, added, changed = assign_contexts(exams, assignment)
    log.info("%d question(s) to add, %d to replace or clear", len(added), len(changed))

    if changed and not force:
        return False, [
            *changed,
            f"{len(changed)} existing context(s) would change; use --force to overwrite them",
        ]
    if not added and not changed:
        return True, [f"{questions_path} already up to date"]

    questions_path.write_text(new_exams.model_dump_json(indent=2) + "\n", encoding="utf-8")
    notes = [f"overwriting {c}" for c in changed]
    notes.append(f"{len(added) + len(changed)} question(s) updated in {questions_path}")
    return True, notes
