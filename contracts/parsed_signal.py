from dataclasses import dataclass, field
from enum import Enum

from contracts.base import BaseContract


class ParsedSignalStatus(str, Enum):
    VALID_SIGNAL = "VALID_SIGNAL"
    PARTIAL_SIGNAL = "PARTIAL_SIGNAL"
    INVALID_SIGNAL = "INVALID_SIGNAL"
    COMMENTARY_ONLY = "COMMENTARY_ONLY"
    CLOSE_SIGNAL = "CLOSE_SIGNAL"
    UPDATE_SIGNAL = "UPDATE_SIGNAL"


@dataclass(frozen=True)
class ParsedSignal(BaseContract):
    raw_message_id: str = ""
    source: str = ""
    status: ParsedSignalStatus = ParsedSignalStatus.INVALID_SIGNAL
    symbol: str | None = None
    action: str | None = None
    entry_type: str | None = None
    entry_price: str | None = None
    stop_loss: str | None = None
    take_profits: list[str] = field(default_factory=list)
    reason: str | None = None
    raw_text: str | None = None

    def __post_init__(self):
        if not self.raw_message_id:
            raise ValueError("ParsedSignal.raw_message_id is required")

        if self.status == ParsedSignalStatus.VALID_SIGNAL:
            missing = []

            if not self.symbol:
                missing.append("symbol")

            if not self.action:
                missing.append("action")

            if not self.stop_loss:
                missing.append("stop_loss")

            if not self.take_profits:
                missing.append("take_profits")

            if missing:
                raise ValueError(
                    f"VALID_SIGNAL missing required fields: {', '.join(missing)}"
                )
