from dataclasses import dataclass
from enum import Enum

from contracts.base import BaseContract


class ExecutionMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


@dataclass(frozen=True)
class ExecutionRequest(BaseContract):
    capital_allocation_id: str = ""
    source: str = ""
    broker: str = "oanda"
    account_id: str | None = None
    strategy_account: str | None = None
    symbol: str = ""
    action: str = ""
    units: int = 0
    entry_price: str | None = None
    take_profit: str | None = None
    stop_loss: str | None = None
    mode: ExecutionMode = ExecutionMode.PAPER
    external_signal_id: str | None = None

    def __post_init__(self):
        if not self.capital_allocation_id:
            raise ValueError("ExecutionRequest.capital_allocation_id is required")

        if self.action not in ["buy", "sell"]:
            raise ValueError("ExecutionRequest.action must be buy or sell")

        if self.units <= 0:
            raise ValueError("ExecutionRequest.units must be greater than 0")

        if not self.symbol:
            raise ValueError("ExecutionRequest.symbol is required")
