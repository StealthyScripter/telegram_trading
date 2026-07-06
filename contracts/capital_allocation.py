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
    risk_amount: float | None = None
    risk_percent: float | None = None
    calculated_units: int | None = None
    reason: str | None = None

    def __post_init__(self):
        if not self.risk_decision_id:
            raise ValueError("CapitalAllocation.risk_decision_id is required")

        if self.units <= 0:
            raise ValueError("CapitalAllocation.units must be greater than 0")

        if self.risk_amount is not None and self.risk_amount < 0:
            raise ValueError("CapitalAllocation.risk_amount cannot be negative")

        if self.risk_percent is not None and self.risk_percent < 0:
            raise ValueError("CapitalAllocation.risk_percent cannot be negative")

        if self.calculated_units is not None and self.calculated_units <= 0:
            raise ValueError("CapitalAllocation.calculated_units must be greater than 0")
