from dataclasses import dataclass

from contracts.base import BaseContract


@dataclass(frozen=True)
class RawMessage(BaseContract):
    source: str = ""
    source_type: str = "telegram"
    source_title: str | None = None
    chat_id: str | None = None
    message_id: str = ""
    posted_at: str = ""
    received_at: str = ""
    raw_text: str = ""

    def __post_init__(self):
        if not self.source:
            raise ValueError("RawMessage.source is required")

        if not self.message_id:
            raise ValueError("RawMessage.message_id is required")

        if not self.raw_text.strip():
            raise ValueError("RawMessage.raw_text is required")
