from contracts.capital_allocation import CapitalAllocation
from contracts.execution_request import ExecutionMode, ExecutionRequest
from contracts.risk_decision import RiskDecision
from contracts.trade_candidate import TradeCandidate


class ExecutionRequestFactory:
    def create(
        self,
        allocation: CapitalAllocation,
        candidate: TradeCandidate,
        risk_decision: RiskDecision,
        mode: ExecutionMode = ExecutionMode.PAPER,
        external_signal_id: str | None = None,
    ) -> ExecutionRequest:
        if allocation.risk_decision_id != risk_decision.id:
            raise ValueError("CapitalAllocation does not match RiskDecision")

        if risk_decision.trade_candidate_id != candidate.id:
            raise ValueError("RiskDecision does not match TradeCandidate")

        take_profit = candidate.take_profits[0] if candidate.take_profits else None

        return ExecutionRequest(
            capital_allocation_id=allocation.id,
            source=candidate.source,
            broker=allocation.broker,
            account_id=allocation.account_id,
            strategy_account=allocation.strategy_account,
            symbol=allocation.symbol,
            action=allocation.action,
            units=allocation.units,
            entry_price=candidate.entry_price,
            take_profit=take_profit,
            stop_loss=candidate.stop_loss,
            mode=mode,
            external_signal_id=external_signal_id or candidate.parsed_signal_id,
        )
