from opox.checks.contexts import _parse_rows
from opox.extract.contexts import QuestionPosition, locate_context

# Part 1 ends with question 3 on page 2; its reserve list restarts at 1 on the same page.
POSITIONS = [
    QuestionPosition(1, 100, 1, "X-1-1"),
    QuestionPosition(1, 300, 2, "X-1-2"),
    QuestionPosition(2, 100, 3, "X-1-3"),
    QuestionPosition(2, 300, 1, "X-1R-1"),
    QuestionPosition(3, 100, 2, "X-1R-2"),
]


def test_locate_context_uses_first_match_from_page() -> None:
    assert locate_context(POSITIONS, 1, 1, 2) == ["X-1-1", "X-1-2"]
    assert locate_context(POSITIONS, 2, 1, 2) == ["X-1R-1", "X-1R-2"]


def test_locate_context_rejects_broken_runs() -> None:
    assert locate_context(POSITIONS, 1, 2, 4) is None
    assert locate_context(POSITIONS, 3, 1, 1) is None


def test_parse_rows_reports_invalid_and_duplicate_rows() -> None:
    rows = [
        {"exam_id": "X", "page": "2", "first": "1", "last": "2"},
        {"exam_id": "X", "page": "2", "first": "3", "last": "4"},
        {"exam_id": "X", "page": "3", "first": "5", "last": "4"},
        {"exam_id": "X", "page": "a", "first": "1", "last": "2"},
    ]
    parsed, errors = _parse_rows(rows)
    assert parsed == [("X", 2, 1, 2)]
    assert len(errors) == 3
