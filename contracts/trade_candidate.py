from dataclasses import dataclass, field
from enum import Enum

from contracts.base import BaseContract


class TradeCandidateStatus(str, Enum):
    APPROVED_FOR_RISK = "APPROVED_FOR_RISK"
    REJECTED = "REJECTED"
    OBSERVE_ONLY = "OBSERVE_ONLY"
    PAPER_ONLY = "PAPER_ONLY"


@dataclass(frozen=True)
class TradeCandidate(BaseContract):
    parsed_signal_id: str = ""
    source: str = ""
    status: TradeCandidateStatus = TradeCandidateStatus.OBSERVE_ONLY
    symbol: str | None = None
    action: str | None = None
    entry_type: str | None = None
    entry_price: str | None = None
    stop_loss: str | None = None
    take_profits: list[str] = field(default_factory=list)
    broker: str | None = None
    strategy_account: str | None = None
    reason: str | None = None
    confidence: float | None = None

    def __post_init__(self):
        if not self.parsed_signal_id:
            raise ValueError("TradeCandidate.parsed_signal_id is required")

        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("TradeCandidate.confidence must be between 0 and 1")
