from dataclasses import dataclass
from enum import Enum

from contracts.risk_decision import RiskDecision, RiskDecisionStatus
from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus
from events.ledger import EventLedger
from events.models import DecisionEvent
from risk.portfolio import PortfolioState, RiskPolicy


class RiskEventType(str, Enum):
    RISK_APPROVED = "RISK_APPROVED"
    RISK_REJECTED = "RISK_REJECTED"
    RISK_LIMIT_BREACH = "RISK_LIMIT_BREACH"
    EXPOSURE_UPDATED = "EXPOSURE_UPDATED"


@dataclass(frozen=True)
class RiskCheckResult:
    approved: bool
    reason: str
    limit_name: str | None = None


class RiskEngine:
    def __init__(
        self,
        policy: RiskPolicy | None = None,
        ledger: EventLedger | None = None,
    ):
        self.policy = policy or RiskPolicy()
        self.ledger = ledger or EventLedger()

    def evaluate(
        self,
        candidate: TradeCandidate,
        portfolio_state: PortfolioState | None = None,
        policy: RiskPolicy | None = None,
    ) -> RiskDecision:
        policy = policy or self.policy
        portfolio_state = portfolio_state or PortfolioState(
            account_id="unknown",
            broker="unknown",
            equity=0,
        )

        if candidate.status != TradeCandidateStatus.APPROVED_FOR_RISK:
            decision = RiskDecision(
                trade_candidate_id=candidate.id,
                status=RiskDecisionStatus.REJECTED,
                reason=candidate.reason or "Candidate not approved for risk",
            )
            self._emit(RiskEventType.RISK_REJECTED, candidate, portfolio_state, decision)
            return decision

        result = self._check(candidate, portfolio_state, policy)
        if not result.approved:
            decision = RiskDecision(
                trade_candidate_id=candidate.id,
                status=RiskDecisionStatus.REJECTED,
                reason=result.reason,
            )
            self._emit(RiskEventType.RISK_LIMIT_BREACH, candidate, portfolio_state, decision)
            self._emit(RiskEventType.RISK_REJECTED, candidate, portfolio_state, decision)
            return decision

        decision = RiskDecision(
            trade_candidate_id=candidate.id,
            status=RiskDecisionStatus.APPROVED,
            reason="Portfolio risk approved",
            max_risk_percent=policy.max_risk_percent,
        )
        self._emit(RiskEventType.EXPOSURE_UPDATED, candidate, portfolio_state, decision)
        self._emit(RiskEventType.RISK_APPROVED, candidate, portfolio_state, decision)
        return decision

    def _check(
        self,
        candidate: TradeCandidate,
        state: PortfolioState,
        policy: RiskPolicy,
    ) -> RiskCheckResult:
        exposure = state.exposure()

        if exposure.total_open_trades >= policy.max_open_trades:
            return RiskCheckResult(False, "Max open trades limit breached", "max_open_trades")

        if state.daily_risk_used >= policy.max_daily_risk:
            return RiskCheckResult(False, "Max daily risk limit breached", "max_daily_risk")

        if state.weekly_risk_used >= policy.max_weekly_risk:
            return RiskCheckResult(False, "Max weekly risk limit breached", "max_weekly_risk")

        symbol = candidate.symbol or ""
        source = candidate.source or ""

        if exposure.symbol_risk.get(symbol, 0.0) >= policy.max_symbol_exposure:
            return RiskCheckResult(False, "Max symbol exposure limit breached", "max_symbol_exposure")

        if exposure.source_risk.get(source, 0.0) >= policy.max_source_exposure:
            return RiskCheckResult(False, "Max source exposure limit breached", "max_source_exposure")

        if exposure.account_risk.get(state.account_id, 0.0) >= policy.max_account_exposure:
            return RiskCheckResult(False, "Max account exposure limit breached", "max_account_exposure")

        if exposure.broker_risk.get(state.broker, 0.0) >= policy.max_broker_exposure:
            return RiskCheckResult(False, "Max broker exposure limit breached", "max_broker_exposure")

        if exposure.total_risk >= policy.max_correlated_exposure:
            return RiskCheckResult(False, "Max correlated exposure limit breached", "max_correlated_exposure")

        return RiskCheckResult(True, "Risk approved")

    def _emit(
        self,
        event_type: RiskEventType,
        candidate: TradeCandidate,
        state: PortfolioState,
        decision: RiskDecision,
    ):
        exposure = state.exposure()
        self.ledger.append(
            DecisionEvent(
                stage="portfolio_risk",
                input_id=candidate.id,
                output_id=decision.id,
                reason=decision.reason,
                payload={
                    "event_type": event_type.value,
                    "trade_candidate_id": candidate.id,
                    "risk_decision_id": decision.id,
                    "account_id": state.account_id,
                    "broker": state.broker,
                    "symbol": candidate.symbol,
                    "source": candidate.source,
                    "status": decision.status.value,
                    "exposure": {
                        "total_open_trades": exposure.total_open_trades,
                        "total_risk": exposure.total_risk,
                        "symbol_risk": exposure.symbol_risk,
                        "source_risk": exposure.source_risk,
                        "account_risk": exposure.account_risk,
                        "broker_risk": exposure.broker_risk,
                    },
                },
            )
        )
