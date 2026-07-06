from contracts.capital_allocation import CapitalAllocation
from contracts.risk_decision import RiskDecision, RiskDecisionStatus
from contracts.trade_candidate import TradeCandidate


class CapitalAllocator:
    def allocate(
        self,
        candidate: TradeCandidate,
        risk_decision: RiskDecision,
        units: int,
        broker: str = "oanda",
        account_id: str | None = None,
        strategy_account: str | None = None,
    ) -> CapitalAllocation:
        if risk_decision.status != RiskDecisionStatus.APPROVED:
            raise ValueError("Cannot allocate capital for rejected risk decision")

        return CapitalAllocation(
            risk_decision_id=risk_decision.id,
            symbol=candidate.symbol or "",
            action=candidate.action or "",
            units=units,
            broker=broker,
            account_id=account_id,
            strategy_account=strategy_account,
            reason="Capital scaffold allocation",
        )
