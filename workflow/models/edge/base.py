from pydantic import BaseModel

from ..node import NodeIdType


class EdgeBase(BaseModel):
    """Base class for all edge types"""

    in_node_id: NodeIdType
    out_node_id: NodeIdType


class SimpleEdge(EdgeBase):
    """Edge model type"""

    pass
