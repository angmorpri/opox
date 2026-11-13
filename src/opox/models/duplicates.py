"""Model for the duplicate groups of an opposition, D011.

Root of `interim/<opposition>/duplicates.json`, written by `opox bank extract duplicates`
and `opox bank add duplicates`.

Notes:
- Only groups of two or more answered questions are listed; any other answered question
  is unique.
- `origin` is `exact` for questions with equal key, and `manual` for groups that join
  several of them through reviewed pairs of `dup_check.csv`.
- `threshold` and `answer_threshold` (0-100) are those used to propose `dup_check.csv`;
  `opox bank add duplicates` reuses them.
- The canonical question is not stored: it is the most recent one, computed when needed.
"""

from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from opox.models.base import StrictModel


class DuplicateGroup(StrictModel):
    members: list[str] = Field(min_length=2)  # question ids, sorted
    origin: Literal["exact", "manual"]

    @field_validator("members")
    @classmethod
    def _check_members(cls, members: list[str]) -> list[str]:
        if members != sorted(set(members)):
            raise ValueError("members must be sorted and unique")
        return members


class DuplicateCollection(StrictModel):
    threshold: float = Field(gt=0, le=100)
    answer_threshold: float = Field(gt=0, le=100)
    groups: list[DuplicateGroup]

    @model_validator(mode="after")
    def _check_disjoint(self) -> Self:
        ids = [m for g in self.groups for m in g.members]
        if len(set(ids)) != len(ids):
            raise ValueError("a question belongs to several groups")
        return self
