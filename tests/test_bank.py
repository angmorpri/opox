import json
from pathlib import Path

from test_dedup import _label, _q, _write

from opox.checks.bank import check_bank
from opox.dedup import commands, contexts
from opox.dedup.pipeline import check_all
from opox.extract.bank import build_bank, extract_bank, make_entry


def test_entry_takes_canonical_and_pools_distractors() -> None:
    old = _q("2019L0A-1-1", "¿Cuál?", ["Sí.", "No.", "Quizá.", "Nunca."], context="c/old.png")
    new = _q("2024L0A-1-1", "¿Cuál es?", ["Nunca", "sí", "Siempre.", "No."], answer=1)
    entry, joined = make_entry("B0001", [old, new])
    assert (entry.canonical, entry.text, entry.answer) == ("2024L0A-1-1", "¿Cuál es?", "sí")
    assert entry.context == old.context
    assert entry.distractors == ["Nunca", "Siempre.", "No.", "Quizá."]
    assert joined == 2


def test_bank_ids_follow_canonical() -> None:
    qs = {q.question_id: q for q in (_q("2024L0A-1-1", "a"), _q("2019L0A-1-1", "b"))}
    bank, _ = build_bank(qs, [["2024L0A-1-1"], ["2019L0A-1-1"]])
    assert [(e.bank_id, e.canonical) for e in bank.root] == [
        ("B0001", "2019L0A-1-1"),
        ("B0002", "2024L0A-1-1"),
    ]


def test_extract_reports_missing_dedup_and_check_detects_changes(tmp_path: Path) -> None:
    _write(
        tmp_path,
        _q("2019L0A-1-1", "¿Qué ley?", ["Ley 39/2015.", "a", "b", "c"]),
        _q("2024L0A-1-1", "¿Qué ley?", ["Ley 39/2015", "a", "d", "c"]),
    )
    ok, notes = extract_bank(tmp_path, "X")
    assert not ok and "no deduplication found" in notes[0]

    assert commands.extract(tmp_path, "X", "answers")[0]
    ok, notes = extract_bank(tmp_path, "X")
    assert not ok and "'stems' is not complete" in notes[0]

    assert commands.extract(tmp_path, "X", "stems")[0]
    assert contexts.extract(tmp_path, "X")[0]
    assert not any(check_all(tmp_path, "X").values())
    ok, notes = extract_bank(tmp_path, "X")
    assert ok
    assert check_bank(tmp_path, "X") == []
    assert "already up to date" in extract_bank(tmp_path, "X")[1][0]

    path = tmp_path / "processed" / "X" / "bank.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data[0]["distractors"] == ["a", "d", "c", "b"]
    data[0]["text"] = "Otro texto"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert check_bank(tmp_path, "X") == ["B0001: text does not match its sources"]
    assert not extract_bank(tmp_path, "X")[0]  # D006
    assert extract_bank(tmp_path, "X", force=True)[0]


def test_check_all_reports_every_stage(tmp_path: Path) -> None:
    _write(
        tmp_path,
        _q("2019L0A-1-1", "a", ["x", "y", "z", "w"]),
        _q("2020L0A-1-1", "b", ["x.", "y", "z", "v"]),
    )
    assert commands.extract(tmp_path, "X", "answers")[0]
    _label(tmp_path, "answers", {})
    results = check_all(tmp_path, "X")
    assert list(results) == ["answers", "stems", "contexts"]
    assert results["answers"] == [] and results["stems"] and results["contexts"]
