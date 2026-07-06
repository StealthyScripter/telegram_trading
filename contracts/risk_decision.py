from dataclasses import dataclass
from enum import Enum

from contracts.base import BaseContract


class RiskDecisionStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class RiskDecision(BaseContract):
    trade_candidate_id: str = ""
    status: RiskDecisionStatus = RiskDecisionStatus.REJECTED
    reason: str | None = None
    max_risk_amount: float | None = None
    max_risk_percent: float | None = None

    def __post_init__(self):
        if not self.trade_candidate_id:
            raise ValueError("RiskDecision.trade_candidate_id is required")

        if self.status == RiskDecisionStatus.REJECTED and not self.reason:
            raise ValueError("Rejected RiskDecision requires reason")
