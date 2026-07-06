from contracts.risk_decision import RiskDecision, RiskDecisionStatus
from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus


class RiskEngine:
    def evaluate(self, candidate: TradeCandidate) -> RiskDecision:
        if candidate.status != TradeCandidateStatus.APPROVED_FOR_RISK:
            return RiskDecision(
                trade_candidate_id=candidate.id,
                status=RiskDecisionStatus.REJECTED,
                reason=candidate.reason or "Candidate not approved for risk",
            )

        return RiskDecision(
            trade_candidate_id=candidate.id,
            status=RiskDecisionStatus.APPROVED,
            reason="Risk scaffold pass-through approval",
        )
