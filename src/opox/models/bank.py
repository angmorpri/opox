"""Model for the question bank (batería de preguntas), D010.

Root of `processed/<opposition>/bank.json`, written by `opox make bank`.

Notes:
- One entry per group of duplicate questions (D011), unique questions included; only
  answered questions are kept.
- `bank_id` is the `question_id` of the canonical question, the most recent of
  `sources`; `text` and `answer` are its own.
- `context` is that of the most recent source with context, relative to
  `data/processed/<opposition>/`.
- `distractors` are the wrong options of every source, joined when equal after the base
  normalization and keeping the text of the most recent source; at least three.
"""

from pathlib import PurePosixPath
from typing import Self

from pydantic import ConfigDict, Field, RootModel, model_validator

from opox.models.base import StrictModel

MIN_DISTRACTORS = 3


class BankQuestion(StrictModel):
    bank_id: str
    sources: list[str] = Field(min_length=1)  # question ids, sorted
    text: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    context: PurePosixPath | None = None
    distractors: list[str] = Field(min_length=MIN_DISTRACTORS)

    @model_validator(mode="after")
    def _check_sources(self) -> Self:
        if self.sources != sorted(set(self.sources)):
            raise ValueError("sources must be sorted and unique")
        if self.bank_id not in self.sources:
            raise ValueError(f"bank_id {self.bank_id!r} not in sources")
        return self


class QuestionBank(RootModel[list[BankQuestion]]):
    """All bank entries of an opposition."""

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _check_unique(self) -> Self:
        sources = [s for e in self.root for s in e.sources]
        if len(set(sources)) != len(sources):
            raise ValueError("a question is the source of several entries")
        return self
