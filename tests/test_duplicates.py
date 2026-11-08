from pathlib import Path, PurePosixPath

from opox.add.duplicates import add_duplicates
from opox.checks.duplicates import check_duplicates, split_by_context
from opox.extract.duplicates import (
    CheckRow,
    DupPaths,
    blocks_of,
    extract_duplicates,
    find_candidates,
    make_groups,
    merge_check_rows,
    read_check_sheet,
)
from opox.make.bank import distractors_of, make_bank
from opox.models.bank import QuestionBank
from opox.models.duplicates import DuplicateCollection
from opox.models.questions import Exam, ExamCollection, Question
from opox.normalize import base_key, extended_key


def q(
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


OPTS = ["Madrid", "Lisboa", "París", "Roma"]
QUESTIONS = [
    q("2019E0A-1-1", "¿Cuál es la capital de España?", OPTS),
    q("2022E0A-1-1", "¿Cual es la capital de España", ["Madrid.", "Berlín", "París", "Oslo"]),
    q("2025L0A-1-1", "¿Cuál es la capital del Reino de España?", OPTS),
    q("2025L0A-1-2", "¿Cuál es el antónimo de TERSO?", ["Rugoso", "Liso", "Suave", "Fino"]),
    q("2025L0A-1-3", "Pregunta anulada", OPTS, answer=None),
]


def by_id(questions: list[Question]) -> dict[str, Question]:
    return {x.question_id: x for x in questions if x.answer is not None}


def test_normalizations() -> None:
    assert base_key("  «Hola»  Mundo. ") == '"hola" mundo'
    assert extended_key("¿Cuál es? =SUMA(A1;B2).") == "cual es =suma(a1;b2)"


def test_make_groups_exact_and_manual() -> None:
    questions = by_id(QUESTIONS)
    groups, notes = make_groups(questions, [])
    assert [(g.members, g.origin) for g in groups] == [(["2019E0A-1-1", "2022E0A-1-1"], "exact")]
    groups, notes = make_groups(questions, [["2019E0A-1-1", "2025L0A-1-1", "X-1-1"]])
    assert [(g.members, g.origin) for g in groups] == [
        (["2019E0A-1-1", "2022E0A-1-1", "2025L0A-1-1"], "manual")
    ]
    assert len(notes) == 1


def test_find_candidates_requires_both_thresholds() -> None:
    questions = by_id(QUESTIONS)
    groups, _ = make_groups(questions, [])
    blocks = blocks_of(questions, groups)
    candidates = find_candidates(questions, blocks, 75, 95)
    assert [c.pair for c in candidates] == [("2022E0A-1-1", "2025L0A-1-1")]
    assert find_candidates(questions, blocks, 95, 95) == []


def test_merge_check_rows_keeps_decisions_and_drops_joined() -> None:
    block_of = {"A": 0, "B": 0, "C": 1, "D": 2}
    old = [
        CheckRow(2, ("A", "B"), 90, 100, "y"),  # joined since
        CheckRow(3, ("A", "C"), 80, 100, "n"),
        CheckRow(4, ("C", "D"), 85, 100, ""),  # pending: regenerated
        CheckRow(5, ("A", "Z"), 70, 100, "y"),  # unknown question
    ]
    from opox.extract.duplicates import Candidate

    candidates = [Candidate(("B", "C"), 81, 100), Candidate(("C", "D"), 85, 100)]
    rows, notes = merge_check_rows(candidates, old, block_of)
    assert [(r.pair, r.same) for r in rows] == [(("C", "D"), ""), (("A", "C"), "n")]
    assert len(notes) == 1


def test_split_by_context() -> None:
    questions = by_id(
        [
            q("2019E0A-1-1", "t", OPTS, context="c/a.png"),
            q("2022E0A-1-1", "t", OPTS, context="c/b.png"),
            q("2025L0A-1-1", "t", OPTS, context="c/c.png"),
            q("2025L0A-1-2", "t", OPTS),
        ]
    )
    block = [sorted(questions)]
    decisions = {
        ("c/a.png", "c/b.png"): "y",
        ("c/a.png", "c/c.png"): "n",
        ("c/b.png", "c/c.png"): "n",
    }
    groups, errors = split_by_context(questions, block, decisions)
    assert errors == []
    assert sorted(groups) == [["2019E0A-1-1", "2022E0A-1-1"], ["2025L0A-1-1", "2025L0A-1-2"]]
    decisions[("c/b.png", "c/c.png")] = "y"
    assert len(split_by_context(questions, block, decisions)[1]) == 1


def test_distractors_joined_and_answers_excluded() -> None:
    questions = sorted(by_id(QUESTIONS).values(), key=lambda x: x.question_id)[:2]
    assert distractors_of(questions[::-1]) == ["Berlín", "París", "Oslo", "Lisboa", "Roma"]


def _write_exams(data_dir: Path, questions: list[Question]) -> None:
    exams = []
    for exam_id in sorted({x.question_id.split("-")[0] for x in questions}):
        exams.append(
            Exam(
                exam_id=exam_id,
                call_id=exam_id[:5],
                model=exam_id[-1],
                source=PurePosixPath(f"tests/{exam_id}T.pdf"),
                key_source=PurePosixPath(f"tests/{exam_id}R.pdf"),
                questions=[x for x in questions if x.question_id.startswith(exam_id)],
            )
        )
    path = data_dir / "processed" / "X" / "questions.json"
    path.parent.mkdir(parents=True)
    path.write_text(ExamCollection(exams).model_dump_json(), encoding="utf-8")


def test_full_flow(tmp_path: Path) -> None:
    _write_exams(tmp_path, QUESTIONS)
    paths = DupPaths.of(tmp_path, "X")
    ok, _ = extract_duplicates(tmp_path, "X")
    assert ok
    errors, warnings, notes = check_duplicates(tmp_path, "X")
    assert errors == [] and warnings == []

    # Review the possible duplicate; check warns until it is added.
    rows, _ = read_check_sheet(paths.check_sheet)
    assert len(rows) == 1
    text = paths.check_sheet.read_text(encoding="utf-8")
    paths.check_sheet.write_text(text.rstrip("\n") + "y\n", encoding="utf-8")
    assert len(check_duplicates(tmp_path, "X")[1]) == 1

    ok, _ = add_duplicates(tmp_path, "X")
    assert ok
    collection = DuplicateCollection.model_validate_json(
        paths.duplicates.read_text(encoding="utf-8")
    )
    assert [g.origin for g in collection.groups] == ["manual"]
    assert read_check_sheet(paths.check_sheet)[0] == []

    # A rerun keeps the manual group.
    ok, _ = extract_duplicates(tmp_path, "X")
    collection = DuplicateCollection.model_validate_json(
        paths.duplicates.read_text(encoding="utf-8")
    )
    assert [len(g.members) for g in collection.groups] == [3]

    ok, _ = make_bank(tmp_path, "X")
    assert ok
    bank = QuestionBank.model_validate_json(
        (tmp_path / "processed" / "X" / "bank.json").read_text(encoding="utf-8")
    )
    assert [(e.bank_id, len(e.sources)) for e in bank.root] == [
        ("2025L0A-1-1", 3),
        ("2025L0A-1-2", 1),
    ]
    assert bank.root[0].distractors == ["Lisboa", "París", "Roma", "Berlín", "Oslo"]


def test_pending_contexts_block_the_bank(tmp_path: Path) -> None:
    questions = [
        q("2019E0A-1-1", "Según la tabla, ¿cuántos?", OPTS, context="contexts/a.png"),
        q("2022E0A-1-1", "Según la tabla, ¿cuántos?", OPTS, context="contexts/b.png"),
    ]
    _write_exams(tmp_path, questions)
    assert extract_duplicates(tmp_path, "X")[0]
    errors = check_duplicates(tmp_path, "X")[0]
    assert errors == [
        f"1 context pair(s) pending review in {DupPaths.of(tmp_path, 'X').contexts_sheet}"
    ]
    assert not make_bank(tmp_path, "X")[0]
