from .base import NodeBase, NodeType
from .body.empty import EmptyNodeBody


class EndNode(NodeBase, EmptyNodeBody):
    """Represents an end node in a workflow.

    End nodes are the exit points of the workflow.
    End nodes can have multiple inputs but no outputs.


    """

    _type = NodeType.end
    color = "yellow"
