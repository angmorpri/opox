"""Models for exam questions (preguntas por examen), D009.

Diagram (Mermaid class diagram):

```mermaid
classDiagram
    direction LR

    class ExamCollection {
        root: list[Exam]
    }
    class Exam {
        exam_id: str
        call_id: str
        model: str
        source: PurePosixPath
        key_source: PurePosixPath
    }
    class Question {
        question_id: str
        part: int
        is_reserve: bool
        number: int
        text: str
        options: list[str]
        answer: int | None
        context: PurePosixPath | None
    }

    ExamCollection *-- "1..*" Exam
    Exam *-- "1..*" Question : questions
    Exam ..> CallRules : call_id
```

Notes:
- `ExamCollection` is the root of `processed/<opposition>/questions.json`; `exam_id`
  is unique within it.
- `exam_id` is the D003 code without the T/R suffix: `call_id` + "0" + `model`
  (e.g. "2025L0A").
- `source` and `key_source` are the exam and answer key PDFs, relative to
  `data/raw/<opposition>/`.
- `question_id` is `<exam_id>-<part>[R]-<number>` (e.g. "2025L0A-1-12", reserve
  "2025L0A-1R-3"); numbering restarts in each part and each reserve list.
- `options` keeps the exam order (a, b, c, d); `answer` is the 0-based index of the
  correct option, or None if the question was annulled.
- `context` is set by `opox tests add contexts` (D005), relative to
  `data/processed/<opposition>/`.
"""

from pathlib import PurePosixPath
from typing import Self

from pydantic import ConfigDict, Field, RootModel, model_validator

from opox.models.base import StrictModel

N_OPTIONS = 4


def make_question_id(exam_id: str, part: int, is_reserve: bool, number: int) -> str:
    """Build the canonical question id."""
    return f"{exam_id}-{part}{'R' if is_reserve else ''}-{number}"


class Question(StrictModel):
    question_id: str
    part: int = Field(ge=1)
    is_reserve: bool
    number: int = Field(ge=1)
    text: str = Field(min_length=1)
    options: list[str] = Field(min_length=N_OPTIONS, max_length=N_OPTIONS)
    answer: int | None = Field(ge=0, lt=N_OPTIONS)
    context: PurePosixPath | None = None


class Exam(StrictModel):
    exam_id: str
    call_id: str
    model: str = Field(pattern=r"^[A-Z]$")
    source: PurePosixPath
    key_source: PurePosixPath
    questions: list[Question] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.exam_id != f"{self.call_id}0{self.model}":
            raise ValueError(f"exam_id {self.exam_id!r} does not match call_id and model")
        seen: set[str] = set()
        for q in self.questions:
            expected = make_question_id(self.exam_id, q.part, q.is_reserve, q.number)
            if q.question_id != expected:
                raise ValueError(f"question_id {q.question_id!r}, expected {expected!r}")
            if q.question_id in seen:
                raise ValueError(f"duplicate question_id {q.question_id!r}")
            seen.add(q.question_id)
        return self


class ExamCollection(RootModel[list[Exam]]):
    """All exams of an opposition."""

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _check_unique_ids(self) -> Self:
        exam_ids = [e.exam_id for e in self.root]
        if len(set(exam_ids)) != len(exam_ids):
            raise ValueError("duplicate exam_id in collection")
        return self
