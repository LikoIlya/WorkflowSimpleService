import enum

from .base import BaseNodeBody


class MessageStatus(str, enum.Enum):
    """Message status enum"""

    pending = "pending"
    sent = "sent"
    opened = "opened"


class MessageNodeBody(BaseNodeBody):
    """Message node body"""

    status: MessageStatus
    message_text: str
