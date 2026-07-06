from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus
from events.ledger import EventLedger
from events.models import DecisionEvent


class StrategyFusionEventType(str, Enum):
    STRATEGY_SIGNAL_RECEIVED = "STRATEGY_SIGNAL_RECEIVED"
    STRATEGY_FUSION_CREATED = "STRATEGY_FUSION_CREATED"
    STRATEGY_FUSION_APPROVED = "STRATEGY_FUSION_APPROVED"
    STRATEGY_FUSION_REJECTED = "STRATEGY_FUSION_REJECTED"


class SignalSourceType(str, Enum):
    TELEGRAM = "telegram"
    MANUAL = "manual"
    WEBHOOK = "webhook"
    TRADINGVIEW = "tradingview"


@dataclass(frozen=True)
class StrategySignal:
    source_type: SignalSourceType
    source_name: str
    candidate: TradeCandidate
    weight: float = 1.0


@dataclass(frozen=True)
class SourceContribution:
    source_type: SignalSourceType
    source_name: str
    symbol: str | None
    action: str | None
    weight: float


@dataclass(frozen=True)
class FusionDecision:
    approved: bool
    reason: str
    candidate: TradeCandidate | None
    contributions: list[SourceContribution] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))


class StrategyFusionEngine:
    def __init__(
        self,
        ledger: EventLedger | None = None,
        minimum_weight: float = 1.0,
    ):
        self.ledger = ledger or EventLedger()
        self.minimum_weight = minimum_weight

    def fuse(self, signals: list[StrategySignal]) -> FusionDecision:
        valid = [signal for signal in signals if self._valid(signal)]

        for signal in valid:
            self._emit(
                StrategyFusionEventType.STRATEGY_SIGNAL_RECEIVED,
                None,
                [self._contribution(signal)],
                "Strategy signal received",
            )

        contributions = [self._contribution(signal) for signal in valid]
        self._emit(
            StrategyFusionEventType.STRATEGY_FUSION_CREATED,
            None,
            contributions,
            "Strategy fusion created",
        )

        if not valid:
            return self._reject("No valid strategy signals", contributions)

        grouped = {}
        for signal in valid:
            key = (signal.candidate.symbol, signal.candidate.action)
            grouped[key] = grouped.get(key, 0.0) + signal.weight

        (symbol, action), weight = max(grouped.items(), key=lambda item: item[1])
        total_weight = sum(signal.weight for signal in valid)

        if weight < self.minimum_weight or weight <= (total_weight - weight):
            return self._reject("Strategy sources disagree", contributions)

        representative = next(
            signal.candidate for signal in valid
            if signal.candidate.symbol == symbol and signal.candidate.action == action
        )
        decision = FusionDecision(
            approved=True,
            reason="Strategy fusion approved",
            candidate=representative,
            contributions=contributions,
        )
        self._emit(
            StrategyFusionEventType.STRATEGY_FUSION_APPROVED,
            decision,
            contributions,
            decision.reason,
        )
        return decision

    def _valid(self, signal: StrategySignal) -> bool:
        candidate = signal.candidate
        return (
            signal.weight > 0
            and candidate.status in {
                TradeCandidateStatus.APPROVED_FOR_RISK,
                TradeCandidateStatus.PAPER_ONLY,
            }
            and bool(candidate.symbol)
            and candidate.action in {"buy", "sell"}
        )

    def _contribution(self, signal: StrategySignal) -> SourceContribution:
        return SourceContribution(
            source_type=signal.source_type,
            source_name=signal.source_name,
            symbol=signal.candidate.symbol,
            action=signal.candidate.action,
            weight=signal.weight,
        )

    def _reject(
        self,
        reason: str,
        contributions: list[SourceContribution],
    ) -> FusionDecision:
        decision = FusionDecision(
            approved=False,
            reason=reason,
            candidate=None,
            contributions=contributions,
        )
        self._emit(
            StrategyFusionEventType.STRATEGY_FUSION_REJECTED,
            decision,
            contributions,
            reason,
        )
        return decision

    def _emit(
        self,
        event_type: StrategyFusionEventType,
        decision: FusionDecision | None,
        contributions: list[SourceContribution],
        reason: str,
    ):
        self.ledger.append(
            DecisionEvent(
                stage="strategy_fusion",
                input_id=",".join(item.source_name for item in contributions) or None,
                output_id=decision.id if decision else None,
                reason=reason,
                payload={
                    "event_type": event_type.value,
                    "approved": decision.approved if decision else None,
                    "contributions": [
                        {
                            "source_type": item.source_type.value,
                            "source_name": item.source_name,
                            "symbol": item.symbol,
                            "action": item.action,
                            "weight": item.weight,
                        }
                        for item in contributions
                    ],
                },
            )
        )
