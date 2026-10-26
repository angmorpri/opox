import csv
from pathlib import Path, PurePosixPath

from opox.cli import _build_parser, _run_dedup_check
from opox.dedup import commands, contexts
from opox.dedup.core import (
    ANSWERS,
    STEMS,
    Member,
    Row,
    build_members,
    canonical,
    find_cases,
    make_collection,
    resolve,
)
from opox.dedup.normalize import base_key, extended_key
from opox.models.questions import Exam, ExamCollection, Question

OPTIONS = ["Uno.", "Dos.", "Tres.", "Cuatro."]


def _q(
    qid: str,
    text: str,
    options: list[str] = OPTIONS,
    answer: int | None = 0,
    context: str | None = None,
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


def _write(data_dir: Path, *questions: Question) -> None:
    path = data_dir / "processed" / "X" / "questions.json"
    path.parent.mkdir(parents=True)
    path.write_text(_exams(*questions).model_dump_json(), encoding="utf-8")


def _label(data_dir: Path, stage: str, labels: dict[str, str], key: int = 4) -> None:
    """Fill in the sheet: `labels` maps the `key` column of a row to its decision."""
    path = data_dir / "interim" / "X" / f"dedup_{stage}_review.csv"
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f, delimiter=";"))
    for row in rows[1:]:
        row[2] = labels.get(row[key], row[2])
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f, delimiter=";").writerows(rows)


def test_normalizations() -> None:
    assert base_key("  «Tres»   —  “dos”. ") == '"tres" - "dos"'
    assert base_key("Álvaro") == "álvaro"
    assert extended_key("¿Cuál es, según él, la opción?") == "cual es segun el la opcion"
    assert extended_key("Año: 3,5") == "año 3,5"


def test_canonical_is_most_recent() -> None:
    qs = [_q("2019L0A-1-1", "a"), _q("2024I0A-1-2", "a"), _q("2024E0A-1-9", "a")]
    assert canonical(qs).question_id == "2024E0A-1-9"


def test_cases_link_similar_members() -> None:
    qs = [
        _q("2019L0A-1-1", "a", ["Ley 39/2015.", "x", "y", "z"]),
        _q("2020L0A-1-1", "b", ["ley 39/2015", "x", "y", "z"]),
        _q("2021L0A-1-1", "c", ["Ley 39/2016.", "x", "y", "z"]),
        _q("2022L0A-1-1", "d", ["Otra cosa.", "x", "y", "z"]),
    ]
    members = build_members([qs], ANSWERS)
    assert [len(m.questions) for m in members] == [2, 1, 1]
    cases = find_cases(members, ANSWERS)
    assert len(cases) == 1
    assert [m.ids for m in cases[0].members] == ["2019L0A-1-1, 2020L0A-1-1", "2021L0A-1-1"]


def test_resolve_joins_labels_and_reports() -> None:
    qs = [
        _q(f"20{n}L0A-1-1", "a", [f"Respuesta {c}.", "x", "y", "z"])
        for n, c in ((19, "A"), (20, "B"), (21, "C"))
    ]
    members = build_members([qs], ANSWERS)
    cases = find_cases(members, ANSWERS)
    ids = [m.ids for m in members]

    rows = [Row(2, "C01", "A", "1", ids[0]), Row(3, "C01", "B", "1", ids[1])]
    res = resolve(members, cases, rows)
    assert res.collection is not None and not res.errors
    assert [len(g.members) for g in res.collection.root] == [2, 1]
    assert res.collection.root[0].canonical == ids[1]
    assert res.missing == [ids[2]]

    rows = [Row(2, "C01", "A", "", ids[0]), Row(3, "C02", "B", "", "1999L0A-1-1")]
    res = resolve(members, cases, rows)
    assert res.pending == 1 and len(res.stale) == 1

    rows = [Row(2, "C01", "A", "1", ids[0]), Row(3, "C02", "B", "1", ids[1])]
    assert resolve(members, cases, rows).errors


def test_stages_end_to_end(tmp_path: Path) -> None:
    _write(
        tmp_path,
        _q("2019L0A-1-1", "¿Qué ley regula el procedimiento?", ["Ley 39/2015.", "a", "b", "c"]),
        _q(
            "2024L0A-1-1", "¿Qué ley regula el procedimiento común?", ["Ley 39/2015", "a", "b", "c"]
        ),
        _q("2024L0A-1-2", "¿Qué ley regula el procedimiento?", ["La Ley 39/2015.", "a", "b", "c"]),
        _q("2024L0A-1-3", "Anulada", answer=None),
    )
    assert commands.extract(tmp_path, "X", "answers")[0]
    assert not commands.extract(tmp_path, "X", "answers")[0]  # D006
    assert any("pending" in e for e in commands.check(tmp_path, "X", "answers"))

    _label(tmp_path, "answers", {"2019L0A-1-1, 2024L0A-1-1": "1", "2024L0A-1-2": "1"})
    assert any("differs" in e for e in commands.check(tmp_path, "X", "answers"))
    assert commands.add(tmp_path, "X", "answers")[0]
    assert commands.check(tmp_path, "X", "answers") == []
    assert "already up to date" in commands.add(tmp_path, "X", "answers")[1][0]

    ok, notes = commands.extract(tmp_path, "X", "answers", force=True)
    assert ok and any("2 decision(s) kept" in n for n in notes)
    assert commands.check(tmp_path, "X", "answers") == []

    assert commands.extract(tmp_path, "X", "stems")[0]
    _label(tmp_path, "stems", {"2019L0A-1-1, 2024L0A-1-2": "a", "2024L0A-1-1": "b"})
    assert commands.add(tmp_path, "X", "stems")[0]
    assert commands.check(tmp_path, "X", "stems") == []
    guide = (tmp_path / "interim" / "X" / "dedup_stems_review.md").read_text(encoding="utf-8")
    assert "Canonical if joined: `2024L0A-1-1`" in guide


def test_stems_require_current_answers(tmp_path: Path) -> None:
    _write(tmp_path, _q("2019L0A-1-1", "a"))
    assert not commands.extract(tmp_path, "X", "stems")[0]
    assert commands.extract(tmp_path, "X", "answers")[0]
    (tmp_path / "processed" / "X" / "questions.json").write_text(
        _exams(_q("2019L0A-1-1", "a"), _q("2019L0A-1-2", "b")).model_dump_json(),
        encoding="utf-8",
    )
    assert any("does not cover" in e for e in commands.check(tmp_path, "X", "stems"))


def test_cli_accepts_prefixes() -> None:
    args = _build_parser().parse_args(["ded", "ch", "st", "C2_AGE"])
    assert (args.action, args.stage, args.func) == ("check", "stems", _run_dedup_check)


def test_stem_stage_key_uses_extended_normalization() -> None:
    assert STEMS.key(_q("2019L0A-1-1", "¿Qué es?")) == "que es"


def test_contexts_stage_splits_different_crops(tmp_path: Path) -> None:
    text = "¿Qué valor hay en la celda B3 de la tabla?"
    _write(
        tmp_path,
        _q("2019L0A-1-1", text, context="contexts/2019L0A_p1.png"),
        _q("2024L0A-1-1", text, context="contexts/2024L0A_p1.png"),
        _q("2024L0A-1-2", text),
        _q("2024L0A-1-3", "Otra pregunta", context="contexts/2024L0A_p1.png"),
    )
    for stage in ("answers", "stems"):
        assert commands.extract(tmp_path, "X", stage)[0]
    assert commands.check(tmp_path, "X", "stems") == []

    assert contexts.extract(tmp_path, "X")[0]
    assert any("pending" in e for e in contexts.check(tmp_path, "X"))
    pair = "contexts/2019L0A_p1.png"
    _label(tmp_path, "contexts", {pair: "y"}, key=0)
    assert contexts.add(tmp_path, "X")[0]
    assert contexts.check(tmp_path, "X") == []
    groups = commands.read_collection(tmp_path / "interim" / "X" / "dedup_contexts.json")[0]
    assert [g.sources for g in groups.root] == [
        ["2019L0A-1-1", "2024L0A-1-1", "2024L0A-1-2"],
        ["2024L0A-1-3"],
    ]

    _label(tmp_path, "contexts", {pair: "n"}, key=0)
    assert contexts.add(tmp_path, "X")[0]
    assert contexts.check(tmp_path, "X") == []
    groups = commands.read_collection(tmp_path / "interim" / "X" / "dedup_contexts.json")[0]
    assert sorted(g.sources for g in groups.root) == [
        ["2019L0A-1-1"],
        ["2024L0A-1-1", "2024L0A-1-2"],
        ["2024L0A-1-3"],
    ]
    ok, notes = contexts.extract(tmp_path, "X", force=True)
    assert ok and any("1 decision(s) kept" in n for n in notes)


def test_contexts_reject_contradictions() -> None:
    crops = ["a.png", "b.png", "c.png"]
    qs = {f"2019L0A-1-{i}": _q(f"2019L0A-1-{i}", "t", context=c) for i, c in enumerate(crops, 1)}
    stems = make_collection([[Member("t", 0, tuple(qs.values()))]])
    inputs = contexts.Inputs(
        qs, stems, {("a.png", "b.png"): [], ("a.png", "c.png"): [], ("b.png", "c.png"): []}
    )
    rows = [
        contexts.Row(2, ("a.png", "b.png"), "y"),
        contexts.Row(3, ("a.png", "c.png"), "n"),
        contexts.Row(4, ("b.png", "c.png"), "y"),
    ]
    assert contexts.resolve(inputs, rows).errors
