from dataclasses import dataclass

from contracts.base import BaseContract


@dataclass(frozen=True)
class CapitalAllocation(BaseContract):
    risk_decision_id: str = ""
    symbol: str = ""
    action: str = ""
    units: int = 0
    broker: str = ""
    account_id: str | None = None
    strategy_account: str | None = None
    reason: str | None = None

    def __post_init__(self):
        if not self.risk_decision_id:
            raise ValueError("CapitalAllocation.risk_decision_id is required")

        if self.units <= 0:
            raise ValueError("CapitalAllocation.units must be greater than 0")
