from typing import Literal

from pydantic import BaseModel

from .base import EdgeBase


class ConditionEdgeContext(BaseModel):
    """Condition edge attributes
    only one attribute is presented


    """

    condition: Literal["Yes", "No"]


class ConditionEdge(EdgeBase, ConditionEdgeContext):
    """Condition edge representation"""

    pass
