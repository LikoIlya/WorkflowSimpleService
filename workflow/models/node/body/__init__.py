from typing import Annotated, Any, Union

from pydantic import Discriminator, Tag

from .condition import ConditionNodeBody
from .empty import EmptyNodeBody
from .message import MessageNodeBody


def get_node_body_type(v: Any) -> str:
    """

    :param v: Any:

    """
    if isinstance(v, dict):
        if v.get("message_text", None) and v.get("status", None):
            return "message"
        elif v.get("rule", None):
            return "condition"
        else:
            return "empty"
    if getattr(v, "message_text", None) and v.get("status", None):
        return "message"
    elif getattr(v, "rule", None):
        return "condition"
    else:
        return "empty"


NodeBody = Annotated[
    Union[
        Annotated[MessageNodeBody, Tag("message")],
        Annotated[ConditionNodeBody, Tag("condition")],
        Annotated[EmptyNodeBody, Tag("empty")],
    ],
    Discriminator(get_node_body_type),
]
