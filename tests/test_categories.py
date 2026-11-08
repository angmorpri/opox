from fractions import Fraction
from pathlib import Path, PurePosixPath

from opox.extract.categories import (
    ADMINISTRATIVE_ACTIVITY,
    OFFICE_SOFTWARE,
    PSYCHOTECHNICAL,
    PUBLIC_ORGANIZATION,
    block_categories,
    extract_categories,
)
from opox.models.categories import CategoryCollection
from opox.models.rules import Block, CallRules, CallRulesCollection, Part, Section

MIXED = Block(
    block_id="II",
    name="Actividad administrativa y ofimática",
    topics=[
        "Atención al público.",
        "Registro y archivo.",
        "Informática básica: hardware.",
        "Word.",
    ],
)


def test_block_categories() -> None:
    assert block_categories(MIXED) == [ADMINISTRATIVE_ACTIVITY] * 2 + [OFFICE_SOFTWARE] * 2
    assert (
        block_categories(Block(block_id="U", topics=["Informática básica.", "Excel."]))
        == [OFFICE_SOFTWARE] * 2
    )
    assert block_categories(Block(block_id="I", name="ORGANIZACIÓN PÚBLICA", topics=["CE."])) == [
        PUBLIC_ORGANIZATION
    ]
    assert block_categories(Block(block_id="II", name="Ofimática", topics=["Word."])) == [
        OFFICE_SOFTWARE
    ]
    assert block_categories(Block(block_id="PSICO", topics=["Aptitudes verbales"])) == [
        PSYCHOTECHNICAL
    ]
    assert block_categories(Block(block_id="X", name="Otra cosa", topics=["Word."])) is None


def _rules(call_id: str, syllabus: list[Block]) -> CallRules:
    return CallRules(
        call_id=call_id,
        source=PurePosixPath(f"rules/{call_id}.pdf"),
        year=int(call_id[:4]),
        access_type=call_id[4],
        duration_minutes=90,
        software_versions="365",
        penalty=Fraction(1, 3),
        parts=[
            Part(
                number=1,
                n_questions=10,
                n_reserve=0,
                sections=[Section(n_questions=10, block_id=syllabus[0].block_id)],
            )
        ],
        syllabus=syllabus,
    )


def _write(data_dir: Path, calls: list[CallRules]) -> None:
    path = data_dir / "processed" / "X" / "rules.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(CallRulesCollection(calls).model_dump_json(), encoding="utf-8")


def _read(data_dir: Path) -> CategoryCollection:
    path = data_dir / "processed" / "X" / "categories.json"
    return CategoryCollection.model_validate_json(path.read_text(encoding="utf-8"))


def test_extract_is_incremental(tmp_path: Path) -> None:
    _write(tmp_path, [_rules("2025L", [MIXED])])
    assert extract_categories(tmp_path, "X")[0]
    first = _read(tmp_path)
    assert [(c.category_id, [len(ct.topics) for ct in c.calls]) for c in first.root] == [
        (1, []),
        (2, [2]),
        (3, [2]),
        (4, []),
    ]
    assert first.root[2].calls[0].topics[0].number == 3

    _write(
        tmp_path,
        [
            _rules("2025L", [MIXED]),
            _rules("2025I", [Block(block_id="U", topics=["Informática básica."])]),
        ],
    )
    ok, notes = extract_categories(tmp_path, "X")
    assert ok and any(n.startswith("ADDED 2025I") for n in notes)
    assert [c.call_id for c in _read(tmp_path).root[2].calls] == ["2025I", "2025L"]
    assert extract_categories(tmp_path, "X")[1][-1] == "No new calls; categories unchanged."


def test_unassignable_block_fails(tmp_path: Path) -> None:
    _write(tmp_path, [_rules("2025L", [Block(block_id="X", topics=["Word."])])])
    ok, _ = extract_categories(tmp_path, "X")
    assert not ok
    assert not (tmp_path / "processed" / "X" / "categories.json").exists()
