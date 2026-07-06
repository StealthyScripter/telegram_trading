from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class TradeEventType(str, Enum):
    SIGNAL_RECEIVED = "SIGNAL_RECEIVED"
    SIGNAL_PARSED = "SIGNAL_PARSED"
    BACKTEST_COMPLETED = "BACKTEST_COMPLETED"
    PAPER_TRADE_CREATED = "PAPER_TRADE_CREATED"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_CANCELED = "ORDER_CANCELED"
    ORDER_REJECTED = "ORDER_REJECTED"
    TRADE_CLOSE_REQUESTED = "TRADE_CLOSE_REQUESTED"
    TRADE_CLOSED = "TRADE_CLOSED"
    DISCREPANCY_DETECTED = "DISCREPANCY_DETECTED"


@dataclass
class TradeEvent:
    event_type: TradeEventType
    source: str | None = None
    signal_id: str | None = None
    trade_id: str | None = None
    broker: str | None = None
    account_id: str | None = None
    symbol: str | None = None
    strategy: str | None = None
    payload: dict = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self):
        data = asdict(self)
        data["event_type"] = self.event_type.value
        return data
