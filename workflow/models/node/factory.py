from pydantic import ValidationError

from .base import NodeType
from .condition import ConditionNode
from .end import EndNode
from .message import MessageNode
from .start import StartNode


class NodeFactory:
    """Factory class for creating nodes."""

    @staticmethod
    def create_node(node_type: NodeType, **kwargs):
        """

        :param node_type: NodeType:
        :param **kwargs:

        """
        from workflow.utils.exceptions import NodeValidationError

        """Creates a node based on the type.

        :param node_type: NodeType: The type of the node to create.
        :type node_type: NodeType
        :param kwargs: key-value attributes passed to node creation
        :raise ValueError: If the node type is not valid.
        :returns: The created node.

        """
        try:
            match node_type:
                case NodeType.start:
                    return StartNode(**kwargs)
                case NodeType.message:
                    return MessageNode(**kwargs)
                case NodeType.condition:
                    return ConditionNode(**kwargs)
                case NodeType.end:
                    return EndNode(**kwargs)
                case _:
                    raise NodeValidationError(
                        f"Invalid node type: {node_type}"
                    )
        except ValidationError as e:
            raise NodeValidationError(e.errors()) from e
