"""Build the question bank from the duplicate groups (D010, D011).

Inputs, for a given opposition: `processed/<opposition>/questions.json` and, in
`interim/<opposition>/`, `duplicates.json`, `dup_contexts.csv` and `dup_check.csv`,
validated as in `opox check duplicates`.

Output: `processed/<opposition>/bank.json` (`QuestionBank`), rebuilt from scratch on
every run: it holds no manual work.
"""

import logging
from collections.abc import Iterable
from pathlib import Path

from opox.checks.duplicates import resolve_duplicates
from opox.extract.duplicates import answer_text, group_context, recency
from opox.models.bank import MIN_DISTRACTORS, BankQuestion, QuestionBank
from opox.models.questions import Question
from opox.normalize import base_key

log = logging.getLogger(__name__)


def distractors_of(questions: list[Question]) -> list[str]:
    """Wrong options of every question, most recent first, joined when equal (base key)."""
    answers = {base_key(answer_text(q)) for q in questions}
    seen: set[str] = set()
    result: list[str] = []
    for q in questions:
        for i, option in enumerate(q.options):
            key = base_key(option)
            if i == q.answer or key in answers or key in seen:
                continue
            seen.add(key)
            result.append(option)
    return result


def make_entry(questions: Iterable[Question]) -> dict:
    """Fields of the bank entry of a group, before validation."""
    ordered = sorted(questions, key=recency)
    top = ordered[0]
    return {
        "bank_id": top.question_id,
        "sources": sorted(q.question_id for q in ordered),
        "text": top.text,
        "answer": answer_text(top),
        "context": group_context(ordered),
        "distractors": distractors_of(ordered),
    }


def make_bank(data_dir: Path, opposition: str) -> tuple[bool, list[str]]:
    """Write the question bank. Return (success, notes)."""
    res = resolve_duplicates(data_dir, opposition)
    if res.errors or res.groups is None:
        return False, [*res.errors, "fix the problems above (`opox check duplicates`) and retry"]

    entries, errors = [], []
    for ids in res.groups:
        fields = make_entry(res.questions[m] for m in ids)
        if len(fields["distractors"]) < MIN_DISTRACTORS:
            errors.append(
                f"{fields['bank_id']}: {len(fields['distractors'])} distractor(s), "
                f"at least {MIN_DISTRACTORS} required"
            )
            continue
        entries.append(BankQuestion.model_validate(fields))
    if errors:
        return False, errors
    bank = QuestionBank(sorted(entries, key=lambda e: e.bank_id))

    bank_path = data_dir / "processed" / opposition / "bank.json"
    bank_path.write_text(bank.model_dump_json(indent=2) + "\n", encoding="utf-8")
    log.info("bank written to %s", bank_path)
    n_distractors = sum(len(e.distractors) for e in bank.root)
    n_joined = sum(len(e.sources) > 1 for e in bank.root)
    return True, [
        *(f"WARNING {w}" for w in res.warnings),
        *res.notes,
        f"{len(bank.root)} entr(ies), {n_joined} from several questions, "
        f"{n_distractors} distractor(s) -> {bank_path}",
    ]
