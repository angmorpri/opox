"""Build the question bank from the deduplicated groups (D010, D011).

Inputs, for a given opposition: `processed/<opposition>/questions.json` and the groups
of the last deduplication stage, `interim/<opposition>/dedup_contexts.json`. Every stage
must pass its check (`opox dedup check all`).

Output: `processed/<opposition>/bank.json`, never overwritten unless forced (D006).
"""

import logging
from collections.abc import Iterable
from pathlib import Path

from opox.dedup.commands import DedupPaths, read_collection
from opox.dedup.contexts import group_context
from opox.dedup.core import answer_text, answered, recency
from opox.dedup.normalize import base_key
from opox.dedup.pipeline import STAGE_ORDER, check_all, started
from opox.models.bank import BankQuestion, QuestionBank
from opox.models.dedup import DedupCollection
from opox.models.questions import ExamCollection, Question

log = logging.getLogger(__name__)


def make_entry(bank_id: str, questions: Iterable[Question]) -> tuple[BankQuestion, int]:
    """Entry for one group of questions; also return how many distractors were joined."""
    ordered = sorted(questions, key=recency)
    top = ordered[0]
    answers = {base_key(answer_text(q)) for q in ordered}
    seen: set[str] = set()
    distractors: list[str] = []
    joined = 0
    for q in ordered:
        for i, option in enumerate(q.options):
            key = base_key(option)
            if i == q.answer or key in answers:
                continue
            if key in seen:
                joined += 1
                continue
            seen.add(key)
            distractors.append(option)
    entry = BankQuestion(
        bank_id=bank_id,
        canonical=top.question_id,
        sources=sorted(q.question_id for q in ordered),
        text=top.text,
        context=group_context(ordered),
        answer=answer_text(top),
        distractors=distractors,
    )
    return entry, joined


def bank_ids(n: int) -> list[str]:
    width = max(4, len(str(n)))
    return [f"B{i:0{width}d}" for i in range(1, n + 1)]


def build_bank(questions: dict[str, Question], groups: list[list[str]]) -> tuple[QuestionBank, int]:
    """Bank from groups of question ids; also return the distractors joined."""
    groups = sorted(
        groups, key=lambda ids: min((questions[s] for s in ids), key=recency).question_id
    )
    entries, joined = [], 0
    for bank_id, ids in zip(bank_ids(len(groups)), groups, strict=True):
        entry, n = make_entry(bank_id, (questions[s] for s in ids))
        entries.append(entry)
        joined += n
    return QuestionBank(entries), joined


def load_questions(path: Path) -> dict[str, Question]:
    exams = ExamCollection.model_validate_json(path.read_text(encoding="utf-8"))
    return {q.question_id: q for q in answered(exams)}


def _dedup_problems(data_dir: Path, opposition: str) -> list[str]:
    """What is missing from the deduplication, briefly; empty if it is complete."""
    if not started(data_dir, opposition):
        return [
            "no deduplication found; run its stages first "
            "(README, section Deduplication; RUNBOOK, steps 6 to 8)"
        ]
    for stage, errors in check_all(data_dir, opposition).items():
        if errors:
            done = STAGE_ORDER[: STAGE_ORDER.index(stage)]
            return [
                f"dedup stage {stage!r} is not complete ({len(errors)} problem(s))"
                + (f"; {', '.join(done)} done" if done else ""),
                f"see `opox dedup check {stage}`",
            ]
    return []


def _changes(old: QuestionBank, new: QuestionBank) -> list[str]:
    """Entries added, removed or changed, matched by their sources."""
    before = {tuple(e.sources): e for e in old.root}
    after = {tuple(e.sources): e for e in new.root}
    changed = [
        k
        for k in before.keys() & after.keys()
        if before[k].model_copy(update={"bank_id": ""})
        != after[k].model_copy(update={"bank_id": ""})
    ]
    return [
        f"{len(after.keys() - before.keys())} entr(ies) added, "
        f"{len(before.keys() - after.keys())} removed, {len(changed)} changed"
    ]


def extract_bank(data_dir: Path, opposition: str, force: bool = False) -> tuple[bool, list[str]]:
    """Write the question bank. Return (written, notes)."""
    questions_path = data_dir / "processed" / opposition / "questions.json"
    bank_path = data_dir / "processed" / opposition / "bank.json"
    if not questions_path.is_file():
        return False, [f"file not found: {questions_path}"]
    problems = _dedup_problems(data_dir, opposition)
    if problems:
        return False, problems

    groups_path = DedupPaths.of(data_dir, opposition, "contexts").json
    collection, _ = read_collection(groups_path)
    assert isinstance(collection, DedupCollection)
    questions = load_questions(questions_path)
    bank, joined = build_bank(questions, [g.sources for g in collection.root])
    n_distractors = sum(len(e.distractors) for e in bank.root)
    log.info("%d repeated option(s) joined", joined)

    notes = []
    if bank_path.exists():
        old = QuestionBank.model_validate_json(bank_path.read_text(encoding="utf-8"))
        if old == bank:
            return True, [f"{bank_path} already up to date"]
        notes = _changes(old, bank)
        if not force:
            return False, [*notes, f"{bank_path} already exists; use --force to overwrite it"]
        notes.append(f"overwriting {bank_path}")
    bank_path.parent.mkdir(parents=True, exist_ok=True)
    bank_path.write_text(bank.model_dump_json(indent=2) + "\n", encoding="utf-8")
    notes.append(
        f"{len(bank.root)} entries, {n_distractors} distractor(s) ({joined} repeated joined) "
        f"written to {bank_path}"
    )
    return True, notes
