from dataclasses import asdict, dataclass
from enum import Enum

from contracts.parsed_signal import ParsedSignal, ParsedSignalStatus
from contracts.trade_candidate import TradeCandidate
from events.ledger import EventLedger
from events.models import DecisionEvent


class MLEventType(str, Enum):
    ML_SIGNAL_SCORED = "ML_SIGNAL_SCORED"
    ML_SIGNAL_REJECTED = "ML_SIGNAL_REJECTED"
    ML_MODEL_VERSION_USED = "ML_MODEL_VERSION_USED"


@dataclass(frozen=True)
class ModelVersion:
    name: str = "rule_based_signal_quality"
    version: str = "1.0.0"

    @property
    def identifier(self) -> str:
        return f"{self.name}:{self.version}"


@dataclass(frozen=True)
class ModelInputFeatures:
    has_entry: bool
    has_stop_loss: bool
    take_profit_count: int
    stop_distance: float | None
    reward_risk_ratio: float | None
    source_score: float | None
    symbol: str | None
    action: str | None
    parse_status: str | None


@dataclass(frozen=True)
class SignalQualityPrediction:
    score: float
    confidence: float
    approved: bool
    reason: str
    model_version: ModelVersion
    features: ModelInputFeatures


@dataclass(frozen=True)
class ModelDecisionContext:
    source_score: float | None = None
    minimum_score: float = 0.5


class MLModel:
    def __init__(
        self,
        model_version: ModelVersion | None = None,
        ledger: EventLedger | None = None,
    ):
        self.model_version = model_version or ModelVersion()
        self.ledger = ledger or EventLedger()

    def extract_features(
        self,
        item: ParsedSignal | TradeCandidate,
        context: ModelDecisionContext | None = None,
    ) -> ModelInputFeatures:
        context = context or ModelDecisionContext()
        entry_price = getattr(item, "entry_price", None)
        stop_loss = getattr(item, "stop_loss", None)
        take_profits = getattr(item, "take_profits", []) or []
        parse_status = getattr(getattr(item, "status", None), "value", None)
        if isinstance(item, TradeCandidate):
            parse_status = None

        stop_distance = None
        reward_risk_ratio = None

        if entry_price and stop_loss:
            entry = float(entry_price)
            stop = float(stop_loss)
            stop_distance = abs(entry - stop)

            if stop_distance > 0 and take_profits:
                first_tp = float(take_profits[0])
                reward_risk_ratio = abs(first_tp - entry) / stop_distance

        return ModelInputFeatures(
            has_entry=bool(entry_price),
            has_stop_loss=bool(stop_loss),
            take_profit_count=len(take_profits),
            stop_distance=stop_distance,
            reward_risk_ratio=reward_risk_ratio,
            source_score=context.source_score,
            symbol=getattr(item, "symbol", None),
            action=getattr(item, "action", None),
            parse_status=parse_status,
        )

    def score(
        self,
        item: ParsedSignal | TradeCandidate,
        context: ModelDecisionContext | None = None,
    ) -> SignalQualityPrediction:
        context = context or ModelDecisionContext()
        features = self.extract_features(item, context)
        score = self._score_features(features)
        approved = score >= context.minimum_score
        reason = "Signal quality approved" if approved else "Signal quality below threshold"
        prediction = SignalQualityPrediction(
            score=score,
            confidence=score,
            approved=approved,
            reason=reason,
            model_version=self.model_version,
            features=features,
        )
        item_id = getattr(item, "id", None)
        self._emit(MLEventType.ML_MODEL_VERSION_USED, item_id, prediction)
        self._emit(
            MLEventType.ML_SIGNAL_SCORED if approved else MLEventType.ML_SIGNAL_REJECTED,
            item_id,
            prediction,
        )
        return prediction

    def _score_features(self, features: ModelInputFeatures) -> float:
        score = 0.0

        if features.symbol:
            score += 0.10
        if features.action in {"buy", "sell"}:
            score += 0.10
        if features.has_entry:
            score += 0.10
        if features.has_stop_loss:
            score += 0.20
        if features.take_profit_count:
            score += min(0.15, 0.05 * features.take_profit_count)
        if features.reward_risk_ratio is not None:
            score += min(0.20, features.reward_risk_ratio / 10)
        if features.source_score is not None:
            score += max(0.0, min(0.10, features.source_score / 1000))
        if features.parse_status == ParsedSignalStatus.VALID_SIGNAL.value:
            score += 0.05

        return round(max(0.0, min(1.0, score)), 4)

    def _emit(
        self,
        event_type: MLEventType,
        item_id: str | None,
        prediction: SignalQualityPrediction,
    ):
        self.ledger.append(
            DecisionEvent(
                stage="ml_signal_quality",
                input_id=item_id,
                output_id=prediction.model_version.identifier,
                reason=prediction.reason,
                payload={
                    "event_type": event_type.value,
                    "score": prediction.score,
                    "confidence": prediction.confidence,
                    "approved": prediction.approved,
                    "model_version": prediction.model_version.identifier,
                    "features": asdict(prediction.features),
                },
            )
        )
