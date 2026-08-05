from typing import Any

from pydantic import BaseModel as PydanticBaseModel


class BaseModel(PydanticBaseModel):
    """Base class for all domain models, backed by Pydantic v2."""

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")
