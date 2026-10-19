"""Shared base for opox data models."""

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Immutable model that rejects unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")
