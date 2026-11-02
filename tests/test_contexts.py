from pathlib import PurePosixPath

from opox.add.contexts import assign_contexts
from opox.checks.contexts import _parse_rows
from opox.extract.contexts import QuestionPosition, locate_context
from opox.models.questions import Exam, ExamCollection, Question

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


def _exams(*contexts: str | None) -> ExamCollection:
    questions = [
        Question(
            question_id=f"2025L0A-1-{n}",
            part=1,
            is_reserve=False,
            number=n,
            text="?",
            options=["a", "b", "c", "d"],
            answer=0,
            context=PurePosixPath(c) if c else None,
        )
        for n, c in enumerate(contexts, start=1)
    ]
    exam = Exam(
        exam_id="2025L0A",
        call_id="2025L",
        model="A",
        source=PurePosixPath("tests/2025L0AT.pdf"),
        key_source=PurePosixPath("tests/2025L0AR.pdf"),
        questions=questions,
    )
    return ExamCollection([exam])


def test_assign_contexts_adds_replaces_and_clears() -> None:
    exams = _exams(None, "contexts/old.png", "contexts/old.png", "contexts/new.png")
    new = PurePosixPath("contexts/new.png")
    assignment = {"2025L0A-1-1": new, "2025L0A-1-2": new, "2025L0A-1-4": new}
    result = assign_contexts(exams, assignment)
    assert [q.context for q in result.root[0].questions] == [new, new, None, new]
