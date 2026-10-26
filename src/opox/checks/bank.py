"""Check the question bank against the extracted questions (D010).

Inputs, for a given opposition: `processed/<opposition>/bank.json`, `questions.json` and
the context crops. The grouping itself is taken as given: the deduplication stages are
checked by `opox dedup check`.

This check is read-only.
"""

import logging
from pathlib import Path

from pydantic import ValidationError

from opox.extract.bank import bank_ids, load_questions, make_entry
from opox.models.bank import QuestionBank

log = logging.getLogger(__name__)


def check_bank(data_dir: Path, opposition: str) -> list[str]:
    """Return the problems found; empty if the bank is consistent with the questions."""
    processed = data_dir / "processed" / opposition
    bank_path, questions_path = processed / "bank.json", processed / "questions.json"
    for path in (bank_path, questions_path):
        if not path.is_file():
            return [f"file not found: {path}"]
    try:
        bank = QuestionBank.model_validate_json(bank_path.read_text(encoding="utf-8"))
    except ValidationError as e:
        return [f"invalid model in {bank_path}\n{e}"]
    questions = load_questions(questions_path)

    sources = {s for e in bank.root for s in e.sources}
    errors = [f"answered question not in the bank: {q}" for q in sorted(questions.keys() - sources)]
    errors += [
        f"unknown or unanswered question in the bank: {q}"
        for q in sorted(sources - questions.keys())
    ]
    if errors:
        return errors

    log.info("checking %d entries", len(bank.root))
    expected_ids = bank_ids(len(bank.root))
    by_canonical = sorted(bank.root, key=lambda e: e.canonical)
    if [e.bank_id for e in by_canonical] != expected_ids:
        errors.append(f"bank_id must be {expected_ids[0]}... in the order of canonical")
    for entry in bank.root:
        expected, _ = make_entry(entry.bank_id, (questions[s] for s in entry.sources))
        for name in ("canonical", "text", "context", "answer", "distractors"):
            if getattr(entry, name) != getattr(expected, name):
                errors.append(f"{entry.bank_id}: {name} does not match its sources")
        if entry.context is not None and not (processed / entry.context).is_file():
            errors.append(f"{entry.bank_id}: context not found: {entry.context}")
    return errors
