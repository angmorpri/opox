"""Models for the official categories and their topics per call, D012.

Root of `processed/<opposition>/categories.json`, written by `opox categories extract`.

Diagram (Mermaid class diagram):

```mermaid
classDiagram
    direction LR

    class CategoryCollection {
        root: list[Category]
    }
    class Category {
        category_id: int
        name: str
    }
    class CallTopics {
        call_id: str
    }
    class Topic {
        block_id: str
        number: int
        text: str
    }

    CategoryCollection *-- "1..*" Category
    Category *-- "0..*" CallTopics : calls
    CallTopics *-- "1..*" Topic : topics
    CallTopics ..> CallRules : call_id
    Topic ..> Block : block_id, number
```

Notes:
- Categories are common to every call; a call without topics in a category is not
  listed in it.
- `block_id` and `number` reference the topic in `rules.json` (D008): `number` is its
  position in the block, from 1; `text` is copied from there.
- Every topic of a call belongs to one category only.
"""

from typing import Self

from pydantic import ConfigDict, Field, RootModel, model_validator

from opox.models.base import StrictModel


class Topic(StrictModel):
    block_id: str
    number: int = Field(ge=1)
    text: str = Field(min_length=1)


class CallTopics(StrictModel):
    call_id: str
    topics: list[Topic] = Field(min_length=1)


class Category(StrictModel):
    category_id: int = Field(ge=1)
    name: str = Field(min_length=1)
    calls: list[CallTopics]

    @model_validator(mode="after")
    def _check_unique_calls(self) -> Self:
        call_ids = [c.call_id for c in self.calls]
        if len(set(call_ids)) != len(call_ids):
            raise ValueError(f"category {self.category_id}: duplicate call_id")
        return self


class CategoryCollection(RootModel[list[Category]]):
    """All categories of an opposition."""

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _check_unique(self) -> Self:
        ids = [c.category_id for c in self.root]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate category_id in collection")
        topics = [
            (call.call_id, t.block_id, t.number)
            for c in self.root
            for call in c.calls
            for t in call.topics
        ]
        if len(set(topics)) != len(topics):
            raise ValueError("a topic belongs to several categories")
        return self
