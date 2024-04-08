import enum
from typing import Annotated, ClassVar

from pydantic import BaseModel, Field, computed_field

NodeIdType = int


class NodeType(str, enum.Enum):
    """Node types enum"""

    start = "start"
    end = "end"
    message = "message"
    condition = "condition"


class NodeBase(BaseModel):
    """Represents a node in a workflow."""

    id: Annotated[NodeIdType, Field(default=None)]
    _type: ClassVar[NodeType]
    color: ClassVar[str]

    @computed_field
    @property
    def type(self) -> NodeType:
        """ """
        return self._type
