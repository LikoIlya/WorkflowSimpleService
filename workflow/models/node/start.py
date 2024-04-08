from .base import NodeBase, NodeType
from .body.empty import EmptyNodeBody


class StartNode(NodeBase, EmptyNodeBody):
    """Represents a start node in the workflow.

    Start nodes are the entry points of the workflow.
    Start nodes have no inputs and only one output.


    """

    _type = NodeType.start
    color = "green"
