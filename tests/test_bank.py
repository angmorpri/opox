from pathlib import PurePosixPath

from opox.add.bank import merge_entries
from opox.extract.bank import (
    exact_groups,
    find_candidates,
    make_entry,
    normalize,
    resolve_bank,
)
from opox.models.questions import Exam, ExamCollection, Question


def _q(
    qid: str, text: str, options: list[str], answer: int | None = 0, context: str | None = None
) -> Question:
    exam_id, part, number = qid.split("-")
    return Question(
        question_id=qid,
        part=int(part.rstrip("R")),
        is_reserve=part.endswith("R"),
        number=int(number),
        text=text,
        options=options,
        answer=answer,
        context=PurePosixPath(context) if context else None,
    )


def _exams(*questions: Question) -> ExamCollection:
    by_exam: dict[str, list[Question]] = {}
    for q in questions:
        by_exam.setdefault(q.question_id.split("-")[0], []).append(q)
    return ExamCollection(
        [
            Exam(
                exam_id=e,
                call_id=e[:5],
                model=e[-1],
                source=PurePosixPath(f"tests/{e}T.pdf"),
                key_source=PurePosixPath(f"tests/{e}R.pdf"),
                questions=qs,
            )
            for e, qs in by_exam.items()
        ]
    )


OPTS = ["Right.", "Wrong one.", "Wrong two.", "Wrong three."]


def test_normalize_keeps_accents_and_case() -> None:
    assert normalize(" “Sólo”  esto. ") == '"Sólo" esto'
    assert normalize("Sólo") != normalize("Solo")
    assert normalize("A – b") == normalize("A - b")


def test_exact_groups_skip_annulled_and_split_contexts() -> None:
    groups = exact_groups(
        _exams(
            _q("2019L0A-1-1", "¿q?", OPTS),
            _q("2024L0A-1-1", "Q?", OPTS[::-1], answer=3),
            _q("2024L0A-1-2", "Q?", OPTS, context="contexts/2024L0A_p1.png"),
            _q("2024L0A-1-3", "Annulled?", OPTS, answer=None),
        )
    )
    assert sorted(len(g.questions) for g in groups) == [1, 2]
    assert {g.rep.question_id for g in groups} == {"2024L0A-1-1", "2024L0A-1-2"}


def test_make_entry_takes_most_recent_and_drops_other_answers() -> None:
    entry = make_entry(
        [
            _q(
                "2019L0A-1-1",
                "Old wording?",
                ["Right (old).", "Wrong one.", "Wrong two.", "Wrong four."],
            ),
            _q("2024L0A-1-5", "New wording?", OPTS),
        ]
    )
    assert entry.bank_id == "2024L0A-1-5"
    assert entry.text == "New wording?"
    assert entry.answer == "Right."
    assert entry.distractors == ["Wrong one.", "Wrong two.", "Wrong three.", "Wrong four."]
    assert entry.sources == ["2019L0A-1-1", "2024L0A-1-5"]


def test_candidates_and_resolution() -> None:
    groups = exact_groups(
        _exams(
            _q("2019L0A-1-1", "¿Cuál es la capital de España?", OPTS),
            _q("2024L0A-1-1", "¿Cuál es hoy la capital de España?", OPTS),
            _q(
                "2019L0A-1-2",
                "Mira la tabla. ¿Qué fila suma más?",
                OPTS,
                context="contexts/2019L0A_p2.png",
            ),
            _q(
                "2024L0A-1-2",
                "Mira la tabla. ¿Qué fila suma más?",
                OPTS,
                context="contexts/2024L0A_p2.png",
            ),
            _q("2024L0A-1-3", "Something unrelated?", OPTS),
        )
    )
    merges, contexts = find_candidates(groups)
    assert [(r["question_a"], r["question_b"], r["reason"]) for r in merges] == [
        ("2019L0A-1-1", "2024L0A-1-1", "text")
    ]
    assert [(r["context_a"], r["context_b"]) for r in contexts] == [
        ("contexts/2019L0A_p2.png", "contexts/2024L0A_p2.png")
    ]

    pending = resolve_bank(groups, merges, contexts)
    assert [e.bank_id for e in pending.entries] == ["2024L0A-1-3"]
    assert pending.pending == 2 and not pending.errors

    merges[0]["merge"] = "y"
    contexts[0]["same"] = "n"
    decided = resolve_bank(groups, merges, contexts)
    assert [(e.bank_id, len(e.sources)) for e in decided.entries] == [
        ("2019L0A-1-2", 1),
        ("2024L0A-1-1", 2),
        ("2024L0A-1-2", 1),
        ("2024L0A-1-3", 1),
    ]


def test_resolution_reports_invalid_and_conflicting_decisions() -> None:
    groups = exact_groups(
        _exams(
            _q("2019L0A-1-1", "Same question one?", OPTS),
            _q("2022L0A-1-1", "Same question two?", OPTS),
            _q("2024L0A-1-1", "Same question six?", OPTS),
        )
    )
    row = {"reason": "text", "note": ""}
    merges = [
        {**row, "question_a": "2019L0A-1-1", "question_b": "2022L0A-1-1", "merge": "y"},
        {**row, "question_a": "2022L0A-1-1", "question_b": "2024L0A-1-1", "merge": "y"},
        {**row, "question_a": "2019L0A-1-1", "question_b": "2024L0A-1-1", "merge": "n"},
        {**row, "question_a": "2019L0A-1-1", "question_b": "2024L0A-1-1", "merge": "maybe"},
    ]
    result = resolve_bank(groups, merges, [])
    assert not result.entries
    assert len(result.errors) == 2


def test_merge_entries_keeps_existing_unless_forced() -> None:
    old = make_entry([_q("2019L0A-1-1", "Q?", OPTS)])
    new = make_entry([_q("2019L0A-1-1", "Q?", OPTS), _q("2024L0A-1-1", "Q!?", OPTS)])
    other = make_entry([_q("2024L0A-1-2", "Other?", OPTS)])

    bank, added, unchanged, conflicts = merge_entries([old], [old, new, other], force=False)
    assert (added, unchanged, len(conflicts)) == (1, 1, 1)
    assert sorted(e.bank_id for e in bank) == ["2019L0A-1-1", "2024L0A-1-2"]

    bank, added, _, _ = merge_entries([old], [new], force=True)
    assert added == 1 and [e.bank_id for e in bank] == ["2024L0A-1-1"]
