from dataclasses import dataclass, field
from enum import Enum

from contracts.parsed_signal import ParsedSignal, ParsedSignalStatus
from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus
from decision.channel_intelligence import ChannelGrade, ChannelIntelligence, DecisionContext
from decision.ensemble import EnsembleDecision
from decision.ml_model import SignalQualityPrediction
from decision.strategy_fusion import FusionDecision
from events.ledger import EventLedger
from events.models import DecisionEvent


class DecisionEventType(str, Enum):
    DECISION_CREATED = "DECISION_CREATED"


class DecisionOutcomeStatus(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    HOLD = "hold"


@dataclass(frozen=True)
class DecisionConfig:
    approve_threshold: float = 0.5
    reject_threshold: float = 0.25
    base_valid_signal_score: float = 0.5
    channel_weight: float = 0.2
    ensemble_weight: float = 0.15
    strategy_fusion_weight: float = 0.1
    ml_advisory_weight: float = 0.05


@dataclass(frozen=True)
class DecisionContribution:
    name: str
    score: float
    weight: float
    value: float
    reason: str


@dataclass(frozen=True)
class DecisionRationale:
    outcome: DecisionOutcomeStatus
    score: float
    reason: str
    contributions: tuple[DecisionContribution, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DecisionOutcome:
    status: DecisionOutcomeStatus
    score: float
    rationale: DecisionRationale
    candidate: TradeCandidate


class DecisionEngine:
    def __init__(
        self,
        channel_intelligence: ChannelIntelligence | None = None,
        config: DecisionConfig | None = None,
        ledger: EventLedger | None = None,
    ):
        self.channel_intelligence = channel_intelligence
        self.config = config or DecisionConfig()
        self.ledger = ledger or EventLedger()
        self.last_context: DecisionContext | None = None

    def evaluate(self, parsed_signal: ParsedSignal) -> TradeCandidate:
        return self.evaluate_decision(parsed_signal).candidate

    def evaluate_decision(
        self,
        parsed_signal: ParsedSignal,
        ensemble_decision: EnsembleDecision | None = None,
        ml_prediction: SignalQualityPrediction | None = None,
        fusion_decision: FusionDecision | None = None,
    ) -> DecisionOutcome:
        context = self._channel_context(parsed_signal)

        if parsed_signal.status != ParsedSignalStatus.VALID_SIGNAL:
            candidate = TradeCandidate(
                parsed_signal_id=parsed_signal.id,
                source=parsed_signal.source,
                status=TradeCandidateStatus.OBSERVE_ONLY,
                symbol=parsed_signal.symbol,
                action=parsed_signal.action,
                entry_type=parsed_signal.entry_type,
                entry_price=parsed_signal.entry_price,
                stop_loss=parsed_signal.stop_loss,
                take_profits=list(parsed_signal.take_profits),
                reason=parsed_signal.reason or "Signal is not valid for risk review",
            )
            outcome = self._outcome(
                status=DecisionOutcomeStatus.HOLD,
                score=0.0,
                reason=candidate.reason,
                candidate=candidate,
                contributions=(),
            )
            self._emit(parsed_signal, outcome)
            return outcome

        if context:
            status = self._status_from_channel_context(context)
            candidate = TradeCandidate(
                parsed_signal_id=parsed_signal.id,
                source=parsed_signal.source,
                status=status,
                symbol=parsed_signal.symbol,
                action=parsed_signal.action,
                entry_type=parsed_signal.entry_type,
                entry_price=parsed_signal.entry_price,
                stop_loss=parsed_signal.stop_loss,
                take_profits=list(parsed_signal.take_profits),
                reason=context.approval_reason,
            )
        else:
            candidate = TradeCandidate(
                parsed_signal_id=parsed_signal.id,
                source=parsed_signal.source,
                status=TradeCandidateStatus.APPROVED_FOR_RISK,
                symbol=parsed_signal.symbol,
                action=parsed_signal.action,
                entry_type=parsed_signal.entry_type,
                entry_price=parsed_signal.entry_price,
                stop_loss=parsed_signal.stop_loss,
                take_profits=list(parsed_signal.take_profits),
                reason="Valid signal approved for risk review",
            )

        score, contributions = self._score(
            context=context,
            ensemble_decision=ensemble_decision,
            ml_prediction=ml_prediction,
            fusion_decision=fusion_decision,
        )
        status = self._outcome_status(candidate, score)
        candidate = self._candidate_for_outcome(candidate, status, score)
        outcome = self._outcome(
            status=status,
            score=score,
            reason=candidate.reason or "Decision created",
            candidate=candidate,
            contributions=contributions,
        )
        self._emit(parsed_signal, outcome)
        return outcome

    def _channel_context(self, parsed_signal: ParsedSignal):
        if not self.channel_intelligence:
            return None

        self.channel_intelligence.record_parsed_signal(parsed_signal)
        self.last_context = self.channel_intelligence.evaluate_source(parsed_signal.source)
        return self.last_context

    def _status_from_channel_context(
        self,
        context: DecisionContext,
    ) -> TradeCandidateStatus:
        if context.grade in {ChannelGrade.REJECTED, ChannelGrade.BLACKLISTED}:
            return TradeCandidateStatus.REJECTED

        if context.grade == ChannelGrade.PAPER:
            return TradeCandidateStatus.PAPER_ONLY

        if context.grade in {ChannelGrade.PROMOTING, ChannelGrade.LIVE}:
            return TradeCandidateStatus.APPROVED_FOR_RISK

        return TradeCandidateStatus.OBSERVE_ONLY

    def _score(
        self,
        context: DecisionContext | None,
        ensemble_decision: EnsembleDecision | None,
        ml_prediction: SignalQualityPrediction | None,
        fusion_decision: FusionDecision | None,
    ) -> tuple[float, tuple[DecisionContribution, ...]]:
        contributions = [
            DecisionContribution(
                name="parsed_signal",
                score=1.0,
                weight=self.config.base_valid_signal_score,
                value=self.config.base_valid_signal_score,
                reason="Parsed signal is valid",
            )
        ]

        if context is not None:
            normalized = max(0.0, min(1.0, context.channel_score / 100))
            contributions.append(
                DecisionContribution(
                    name="channel_intelligence",
                    score=normalized,
                    weight=self.config.channel_weight,
                    value=normalized * self.config.channel_weight,
                    reason=context.approval_reason,
                )
            )

        if ensemble_decision is not None:
            normalized = ensemble_decision.consensus_score.score if ensemble_decision.approved else 0.0
            contributions.append(
                DecisionContribution(
                    name="ensemble",
                    score=normalized,
                    weight=self.config.ensemble_weight,
                    value=normalized * self.config.ensemble_weight,
                    reason=ensemble_decision.reason,
                )
            )

        if fusion_decision is not None:
            normalized = 1.0 if fusion_decision.approved else 0.0
            contributions.append(
                DecisionContribution(
                    name="strategy_fusion",
                    score=normalized,
                    weight=self.config.strategy_fusion_weight,
                    value=normalized * self.config.strategy_fusion_weight,
                    reason=fusion_decision.reason,
                )
            )

        if ml_prediction is not None:
            normalized = max(0.0, min(1.0, ml_prediction.score))
            contributions.append(
                DecisionContribution(
                    name="ml_advisory",
                    score=normalized,
                    weight=self.config.ml_advisory_weight,
                    value=normalized * self.config.ml_advisory_weight,
                    reason=ml_prediction.reason,
                )
            )

        total = round(min(1.0, sum(item.value for item in contributions)), 4)
        return total, tuple(contributions)

    def _outcome_status(
        self,
        candidate: TradeCandidate,
        score: float,
    ) -> DecisionOutcomeStatus:
        if candidate.status == TradeCandidateStatus.REJECTED:
            return DecisionOutcomeStatus.REJECT

        if score >= self.config.approve_threshold and candidate.status in {
            TradeCandidateStatus.APPROVED_FOR_RISK,
            TradeCandidateStatus.PAPER_ONLY,
        }:
            return DecisionOutcomeStatus.APPROVE

        if score <= self.config.reject_threshold:
            return DecisionOutcomeStatus.REJECT

        return DecisionOutcomeStatus.HOLD

    def _candidate_for_outcome(
        self,
        candidate: TradeCandidate,
        status: DecisionOutcomeStatus,
        score: float,
    ) -> TradeCandidate:
        if status == DecisionOutcomeStatus.APPROVE:
            return candidate

        if status == DecisionOutcomeStatus.REJECT:
            return TradeCandidate(
                parsed_signal_id=candidate.parsed_signal_id,
                source=candidate.source,
                status=TradeCandidateStatus.REJECTED,
                symbol=candidate.symbol,
                action=candidate.action,
                entry_type=candidate.entry_type,
                entry_price=candidate.entry_price,
                stop_loss=candidate.stop_loss,
                take_profits=list(candidate.take_profits),
                confidence=candidate.confidence,
                strategy_account=candidate.strategy_account,
                reason=f"Decision rejected with score {score}",
            )

        return TradeCandidate(
            parsed_signal_id=candidate.parsed_signal_id,
            source=candidate.source,
            status=TradeCandidateStatus.OBSERVE_ONLY,
            symbol=candidate.symbol,
            action=candidate.action,
            entry_type=candidate.entry_type,
            entry_price=candidate.entry_price,
            stop_loss=candidate.stop_loss,
            take_profits=list(candidate.take_profits),
            confidence=candidate.confidence,
            strategy_account=candidate.strategy_account,
            reason=f"Decision held with score {score}",
        )

    def _outcome(
        self,
        status: DecisionOutcomeStatus,
        score: float,
        reason: str,
        candidate: TradeCandidate,
        contributions: tuple[DecisionContribution, ...],
    ) -> DecisionOutcome:
        rationale = DecisionRationale(
            outcome=status,
            score=score,
            reason=reason,
            contributions=contributions,
        )
        return DecisionOutcome(
            status=status,
            score=score,
            rationale=rationale,
            candidate=candidate,
        )

    def _emit(
        self,
        parsed_signal: ParsedSignal,
        outcome: DecisionOutcome,
    ):
        self.ledger.append(
            DecisionEvent(
                stage="decision",
                input_id=parsed_signal.id,
                output_id=outcome.candidate.id,
                reason=outcome.rationale.reason,
                payload={
                    "event_type": DecisionEventType.DECISION_CREATED.value,
                    "parsed_signal_id": parsed_signal.id,
                    "trade_candidate_id": outcome.candidate.id,
                    "outcome": outcome.status.value,
                    "score": outcome.score,
                    "candidate_status": outcome.candidate.status.value,
                    "contributions": [
                        {
                            "name": item.name,
                            "score": item.score,
                            "weight": item.weight,
                            "value": item.value,
                            "reason": item.reason,
                        }
                        for item in outcome.rationale.contributions
                    ],
                },
            )
        )
