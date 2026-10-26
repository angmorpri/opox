"""Models for the deduplication stages of answers and stems (D011).

Diagram (Mermaid class diagram):

```mermaid
classDiagram
    direction LR

    class DedupCollection {
        root: list[DedupGroup]
    }
    class DedupGroup {
        canonical: str
    }
    class DedupMember {
        key: str
        sources: list[str]
    }

    DedupCollection *-- "1..*" DedupGroup
    DedupGroup *-- "1..*" DedupMember : members
    DedupMember ..> Question : sources
```

Notes:
- `DedupCollection` is the root of `interim/<opposition>/dedup_answers.json` and
  `dedup_stems.json`. Every answered question is in exactly one `sources`.
- A member gathers the questions whose normalized answer (or stem) `key` is equal; a
  group with 2+ members was joined in the manual review.
- `canonical` is the `question_id` of the most recent question of the group (D011).
- Groups are sorted by `canonical`; members by their first source; sources by
  `question_id`.
"""

from typing import Self

from pydantic import ConfigDict, Field, RootModel, model_validator

from opox.models.base import StrictModel


class DedupMember(StrictModel):
    key: str
    sources: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_sorted(self) -> Self:
        if self.sources != sorted(set(self.sources)):
            raise ValueError(f"sources of {self.key!r} must be sorted and unique")
        return self


class DedupGroup(StrictModel):
    canonical: str
    members: list[DedupMember] = Field(min_length=1)

    @property
    def sources(self) -> list[str]:
        return sorted(s for m in self.members for s in m.sources)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.canonical not in self.sources:
            raise ValueError(f"canonical {self.canonical!r} not in sources")
        firsts = [m.sources[0] for m in self.members]
        if firsts != sorted(firsts):
            raise ValueError(f"{self.canonical}: members must be sorted by first source")
        return self


class DedupCollection(RootModel[list[DedupGroup]]):
    """All deduplication groups of one stage."""

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        canonicals = [g.canonical for g in self.root]
        if canonicals != sorted(canonicals):
            raise ValueError("groups must be sorted by canonical")
        sources = [s for g in self.root for s in g.sources]
        if len(set(sources)) != len(sources):
            raise ValueError("a question appears in more than one group")
        return self
