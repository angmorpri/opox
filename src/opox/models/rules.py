"""Models for exam call rules (bases de convocatoria).

Diagram (Mermaid class diagram):

```mermaid
classDiagram
    direction LR

    class CallRulesCollection {
        root: list[CallRules]
    }
    class CallRules {
        call_id: str
        source: PurePosixPath
        year: int
        access_type: AccessType
        duration_minutes: int
        software_versions: str
        penalty: Fraction
    }
    class Part {
        number: int
        n_questions: int
        n_reserve: int
    }
    class Section {
        n_questions: int
        block_id: str
    }
    class Block {
        block_id: str
        name: str | None
        topics: list[str]
    }
    class AccessType {
        <<enumeration>>
        OPEN = "L"
        INTERNAL = "I"
        STABILIZATION = "E"
    }

    CallRulesCollection *-- "1..*" CallRules
    CallRules *-- "1..*" Part : parts
    CallRules *-- "1..*" Block : syllabus
    Part *-- "1..*" Section : sections
    Section ..> Block : block_id
    CallRules --> AccessType
```

Notes:
- `CallRulesCollection` is the root of `processed/<opposition>/rules.json`; `call_id`
  is unique within it.
- `call_id` is `year` + `access_type` (e.g. "2025L").
- `source` is relative to `data/raw/<opposition>/`, always with POSIX separators.
- `penalty` is the fraction of a correct answer subtracted per wrong answer ("1/3").
- `Part.number` is consecutive from 1; `Part.n_questions` equals the sum of its sections.
- `Part.sections` are listed in exam order; reserve questions belong to no section.
- `Section.block_id` must reference a `Block` in the syllabus.
- `Block.block_id` follows D008 ("I", "II", "PSICO", "U"...).
- Topic number is its index in `Block.topics` + 1.
"""

from enum import StrEnum
from fractions import Fraction
from pathlib import PurePosixPath
from typing import Self

from pydantic import ConfigDict, Field, RootModel, model_validator

from opox.models.base import StrictModel

PSYCHOTECHNICAL_BLOCK_ID = "PSICO"


class AccessType(StrEnum):
    OPEN = "L"
    INTERNAL = "I"
    STABILIZATION = "E"


class Section(StrictModel):
    n_questions: int = Field(gt=0)
    block_id: str


class Part(StrictModel):
    number: int = Field(ge=1)
    n_questions: int = Field(gt=0)
    n_reserve: int = Field(ge=0)
    sections: list[Section] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_section_total(self) -> Self:
        total = sum(s.n_questions for s in self.sections)
        if total != self.n_questions:
            raise ValueError(
                f"part {self.number}: sections sum {total}, expected {self.n_questions}"
            )
        return self


class Block(StrictModel):
    block_id: str
    name: str | None = None
    topics: list[str] = Field(min_length=1)  # topic number = index + 1


class CallRules(StrictModel):
    call_id: str  # "2025L"
    source: PurePosixPath  # relative to data/raw/<opposition>/; POSIX for portable JSON
    year: int
    access_type: AccessType
    duration_minutes: int = Field(gt=0)
    software_versions: str
    penalty: Fraction  # fraction of a correct answer subtracted per error
    parts: list[Part] = Field(min_length=1)
    syllabus: list[Block] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.call_id != f"{self.year}{self.access_type}":
            raise ValueError(f"call_id {self.call_id!r} does not match year and access_type")
        if [p.number for p in self.parts] != list(range(1, len(self.parts) + 1)):
            raise ValueError("parts must be numbered consecutively from 1")
        block_ids = [b.block_id for b in self.syllabus]
        if len(set(block_ids)) != len(block_ids):
            raise ValueError("duplicate block_id in syllabus")
        missing = {s.block_id for p in self.parts for s in p.sections} - set(block_ids)
        if missing:
            raise ValueError(f"sections reference unknown blocks: {sorted(missing)}")
        return self


class CallRulesCollection(RootModel[list[CallRules]]):
    """All call rules of an opposition."""

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _check_unique_ids(self) -> Self:
        call_ids = [r.call_id for r in self.root]
        if len(set(call_ids)) != len(call_ids):
            raise ValueError("duplicate call_id in collection")
        return self
