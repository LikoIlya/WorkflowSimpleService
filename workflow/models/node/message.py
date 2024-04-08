from .base import NodeBase, NodeType
from .body.message import MessageNodeBody


class MessageNode(NodeBase, MessageNodeBody):
    """Represents a node in a workflow that sends a message."""

    _type = NodeType.message
    color = "blue"
