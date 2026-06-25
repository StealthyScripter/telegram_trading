from dataclasses import dataclass, field
from enum import Enum
from typing import Literal
from datetime import datetime, timezone
from controls.trade_controls import OpenTradePolicy


class ExecutionStatus(str, Enum):
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"
    UNKNOWN = "UNKNOWN"
    DISCREPANCY = "DISCREPANCY"


TradeAction = Literal["buy", "sell"]


@dataclass
class TradeRequest:
    symbol: str
    action: TradeAction
    units: int
    source: str
    strategy_account: str | None = None
    broker_account_id: str | None = None
    entry_price: str | None = None
    take_profit: str | None = None
    stop_loss: str | None = None
    broker: str = "oanda"
    external_signal_id: str | None = None
    open_trade_policy: OpenTradePolicy = OpenTradePolicy.REJECT_IF_EXISTS
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ExecutionResult:
    status: ExecutionStatus
    broker: str
    account_id: str
    symbol: str
    action: str
    requested_units: int
    broker_trade_id: str | None = None
    broker_order_id: str | None = None
    reason: str | None = None
    raw_response: dict | None = None
