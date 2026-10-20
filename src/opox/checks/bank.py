"""Check the question bank against the extracted questions (D010).

Inputs, for a given opposition: `processed/<opposition>/bank.json` and `questions.json`.

This check is read-only.
"""

import logging
from pathlib import Path

from pydantic import ValidationError

from opox.extract.bank import BankPaths
from opox.models.bank import QuestionBank
from opox.models.questions import ExamCollection

log = logging.getLogger(__name__)


def check_bank(data_dir: Path, opposition: str) -> list[str]:
    """Return a list of problems found; empty if every answered question is in the bank."""
    paths = BankPaths.of(data_dir, opposition)
    for path in (paths.bank, paths.questions):
        if not path.is_file():
            return [f"file not found: {path}"]
    try:
        bank = QuestionBank.model_validate_json(paths.bank.read_text(encoding="utf-8"))
    except ValidationError as e:
        return [f"invalid model in {paths.bank}\n{e}"]
    exams = ExamCollection.model_validate_json(paths.questions.read_text(encoding="utf-8"))
    answered = {q.question_id: q for e in exams.root for q in e.questions if q.answer is not None}
    log.info("checking %d entries against %d answered questions", len(bank.root), len(answered))

    errors: list[str] = []
    for entry in bank.root:
        unknown = [s for s in entry.sources if s not in answered]
        if unknown:
            errors.append(f"{entry.bank_id}: unknown or annulled sources {', '.join(unknown)}")
            continue
        rep = answered[entry.bank_id]
        assert rep.answer is not None
        if (entry.text, entry.context, entry.answer) != (
            rep.text,
            rep.context,
            rep.options[rep.answer],
        ):
            errors.append(f"{entry.bank_id}: text, context or answer differ from {paths.questions}")

    covered = {s for e in bank.root for s in e.sources}
    missing = sorted(answered.keys() - covered)
    if missing:
        errors.append(
            f"{len(missing)} answered question(s) not in the bank: {', '.join(missing)}\n"
            "Did you complete the control sheets and run `opox add bank`?"
        )
    return errors
