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
        canonical: str
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
- `bank_id` ("B0001"...) follows the order of `canonical`; it may change when the bank
  is regenerated.
- `sources` are the `question_id`s of every appearance in `questions.json` (D009).
- `canonical` is the most recent source (D011); `text` and `answer` are its own.
- `context` is that of the most recent source with context (D011), relative to
  `data/processed/<opposition>/`.
- `distractors` pools the wrong options of all sources, joined when equal after the
  base normalization (D011): those of the canonical first, then by recency.
"""

from pathlib import PurePosixPath
from typing import Self

from pydantic import ConfigDict, Field, RootModel, model_validator

from opox.dedup.normalize import base_key
from opox.models.base import StrictModel
from opox.models.questions import N_OPTIONS

N_DISTRACTORS = N_OPTIONS - 1


class BankQuestion(StrictModel):
    bank_id: str = Field(pattern=r"^B\d{4,}$")
    canonical: str
    sources: list[str] = Field(min_length=1)
    text: str = Field(min_length=1)
    context: PurePosixPath | None = None
    answer: str = Field(min_length=1)
    distractors: list[str] = Field(min_length=N_DISTRACTORS)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.sources != sorted(set(self.sources)):
            raise ValueError(f"{self.bank_id}: sources must be sorted and unique")
        if self.canonical not in self.sources:
            raise ValueError(f"{self.bank_id}: canonical {self.canonical!r} not in sources")
        keys = [base_key(d) for d in self.distractors]
        if len(set(keys)) != len(keys):
            raise ValueError(f"{self.bank_id}: duplicate distractors")
        if base_key(self.answer) in keys:
            raise ValueError(f"{self.bank_id}: answer listed as distractor")
        return self


class QuestionBank(RootModel[list[BankQuestion]]):
    """All unique questions of an opposition."""

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        bank_ids = [q.bank_id for q in self.root]
        if bank_ids != sorted(set(bank_ids)):
            raise ValueError("bank_id must be unique and sorted")
        sources = [s for q in self.root for s in q.sources]
        if len(set(sources)) != len(sources):
            raise ValueError("a source question appears in more than one entry")
        return self
