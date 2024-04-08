# flake8: noqa
from typing import Annotated, Any, Union

from pydantic import Discriminator, Tag

from .base import NodeIdType, NodeType
from .body import *
from .condition import ConditionNode
from .end import EndNode
from .factory import NodeFactory
from .message import MessageNode
from .start import StartNode


def get_node_type(v: Any) -> NodeType:
    """

    :param v: Any:

    """
    if isinstance(v, dict):
        type_key = v.get("type", None)
    else:
        type_key = getattr(v, "type", None)
    return NodeType(type_key) if type_key else None


ValidNode = Annotated[
    Union[
        Annotated[MessageNode, Tag(NodeType.message)],
        Annotated[ConditionNode, Tag(NodeType.condition)],
        Annotated[StartNode, Tag(NodeType.start)],
        Annotated[EndNode, Tag(NodeType.end)],
    ],
    Discriminator(get_node_type),
]
