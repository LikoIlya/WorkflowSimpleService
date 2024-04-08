# flake8: noqa
from .base import SimpleEdge
from .condition import ConditionEdge, ConditionEdgeContext

Edge = ConditionEdge | SimpleEdge
EdgeContext = ConditionEdgeContext | None

__all__ = ["Edge", "EdgeContext"]
