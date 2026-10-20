"""Models for the question bank (batería de preguntas), D010.

Diagram (Mermaid class diagram):

```mermaid
classDiagram
    direction LR

    class QuestionBank {
        root: list[BankQuestion]
    }
    class BankQuestion {
        bank_id: str
        sources: list[str]
        text: str
        context: PurePosixPath | None
        answer: str
        distractors: list[str]
    }

    QuestionBank *-- "1..*" BankQuestion
    BankQuestion ..> Question : sources
```

Notes:
- `QuestionBank` is the root of `processed/<opposition>/bank.json`, sorted by `bank_id`.
- `sources` are the `question_id`s of every appearance in `questions.json` (D009).
- `bank_id` is the `question_id` of the representative: the most recent appearance. Its
  `text`, `context` and `answer` are the canonical ones.
- `distractors` pools the wrong options of all appearances, deduplicated. An exam takes
  `N_DISTRACTORS` of them at random and shuffles them with the answer.
- `context` is relative to `data/processed/<opposition>/`, as in `Question.context`.
"""

from pathlib import PurePosixPath
from typing import Self

from pydantic import ConfigDict, Field, RootModel, model_validator

from opox.models.base import StrictModel
from opox.models.questions import N_OPTIONS

N_DISTRACTORS = N_OPTIONS - 1


class BankQuestion(StrictModel):
    bank_id: str
    sources: list[str] = Field(min_length=1)
    text: str = Field(min_length=1)
    context: PurePosixPath | None = None
    answer: str = Field(min_length=1)
    distractors: list[str] = Field(min_length=N_DISTRACTORS)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.bank_id not in self.sources:
            raise ValueError(f"bank_id {self.bank_id!r} not in sources")
        if len(set(self.sources)) != len(self.sources):
            raise ValueError(f"{self.bank_id}: duplicate sources")
        if len(set(self.distractors)) != len(self.distractors):
            raise ValueError(f"{self.bank_id}: duplicate distractors")
        if self.answer in self.distractors:
            raise ValueError(f"{self.bank_id}: answer listed as distractor")
        return self


class QuestionBank(RootModel[list[BankQuestion]]):
    """All unique questions of an opposition."""

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _check_unique_ids(self) -> Self:
        bank_ids = [q.bank_id for q in self.root]
        if len(set(bank_ids)) != len(bank_ids):
            raise ValueError("duplicate bank_id in bank")
        sources = [s for q in self.root for s in q.sources]
        if len(set(sources)) != len(sources):
            raise ValueError("a source question appears in more than one entry")
        return self
