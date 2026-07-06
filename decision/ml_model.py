from dataclasses import asdict, dataclass, field
from enum import Enum

from contracts.parsed_signal import ParsedSignal, ParsedSignalStatus
from contracts.trade_candidate import TradeCandidate
from events.ledger import EventLedger
from events.models import DecisionEvent


class MLEventType(str, Enum):
    ML_SIGNAL_SCORED = "ML_SIGNAL_SCORED"
    ML_SIGNAL_REJECTED = "ML_SIGNAL_REJECTED"
    ML_MODEL_VERSION_USED = "ML_MODEL_VERSION_USED"
    ML_SHADOW_PREDICTION_CREATED = "ML_SHADOW_PREDICTION_CREATED"
    ML_DRIFT_REPORT_CREATED = "ML_DRIFT_REPORT_CREATED"
    ML_TRAINING_DATASET_VALIDATED = "ML_TRAINING_DATASET_VALIDATED"


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
class TrainingExample:
    features: ModelInputFeatures
    label: float
    example_id: str | None = None


@dataclass(frozen=True)
class TrainingDataset:
    examples: tuple[TrainingExample, ...]
    model_version: ModelVersion


@dataclass(frozen=True)
class EvaluationReport:
    model_version: ModelVersion
    example_count: int
    average_label: float
    average_prediction: float
    mean_absolute_error: float


@dataclass(frozen=True)
class DriftReport:
    model_version: ModelVersion
    baseline_average_score: float
    current_average_score: float
    drift_score: float
    drift_detected: bool
    threshold: float


@dataclass(frozen=True)
class ConfidenceCalibration:
    raw_confidence: float
    calibrated_confidence: float
    method: str = "bounded_linear"


@dataclass(frozen=True)
class ShadowPrediction:
    prediction: SignalQualityPrediction
    advisory_only: bool = True
    affects_execution: bool = False
    metadata: dict = field(default_factory=dict)


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

        features = ModelInputFeatures(
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
        self.validate_features(features)
        return features

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

    def validate_features(self, features: ModelInputFeatures) -> None:
        if not isinstance(features.has_entry, bool):
            raise ValueError("ModelInputFeatures.has_entry must be bool")
        if not isinstance(features.has_stop_loss, bool):
            raise ValueError("ModelInputFeatures.has_stop_loss must be bool")
        if not isinstance(features.take_profit_count, int) or features.take_profit_count < 0:
            raise ValueError("ModelInputFeatures.take_profit_count must be a non-negative integer")
        for name in ["stop_distance", "reward_risk_ratio", "source_score"]:
            value = getattr(features, name)
            if value is not None and not isinstance(value, (int, float)):
                raise ValueError(f"ModelInputFeatures.{name} must be numeric")
        if features.stop_distance is not None and features.stop_distance < 0:
            raise ValueError("ModelInputFeatures.stop_distance cannot be negative")
        if features.reward_risk_ratio is not None and features.reward_risk_ratio < 0:
            raise ValueError("ModelInputFeatures.reward_risk_ratio cannot be negative")

    def validate_dataset(self, dataset: TrainingDataset) -> None:
        if not dataset.examples:
            raise ValueError("TrainingDataset.examples cannot be empty")
        for example in dataset.examples:
            self.validate_features(example.features)
            if not isinstance(example.label, (int, float)):
                raise ValueError("TrainingExample.label must be numeric")
            if not 0 <= example.label <= 1:
                raise ValueError("TrainingExample.label must be between 0 and 1")
        self._emit_dataset_event(dataset, "Training dataset validated")

    def train_offline(self, dataset: TrainingDataset) -> EvaluationReport:
        self.validate_dataset(dataset)
        predictions = [self._score_features(example.features) for example in dataset.examples]
        labels = [float(example.label) for example in dataset.examples]
        errors = [abs(prediction - label) for prediction, label in zip(predictions, labels)]
        return EvaluationReport(
            model_version=dataset.model_version,
            example_count=len(dataset.examples),
            average_label=round(sum(labels) / len(labels), 4),
            average_prediction=round(sum(predictions) / len(predictions), 4),
            mean_absolute_error=round(sum(errors) / len(errors), 4),
        )

    def shadow_predict(
        self,
        item: ParsedSignal | TradeCandidate,
        context: ModelDecisionContext | None = None,
    ) -> ShadowPrediction:
        prediction = self.score(item, context)
        shadow = ShadowPrediction(
            prediction=prediction,
            metadata={"model_version": prediction.model_version.identifier},
        )
        self.ledger.append(
            DecisionEvent(
                stage="ml_signal_quality",
                input_id=getattr(item, "id", None),
                output_id=prediction.model_version.identifier,
                reason="Shadow prediction created",
                payload={
                    "event_type": MLEventType.ML_SHADOW_PREDICTION_CREATED.value,
                    "advisory_only": shadow.advisory_only,
                    "affects_execution": shadow.affects_execution,
                    "score": prediction.score,
                    "model_version": prediction.model_version.identifier,
                },
            )
        )
        return shadow

    def calibrate_confidence(self, raw_confidence: float) -> ConfidenceCalibration:
        if not isinstance(raw_confidence, (int, float)):
            raise ValueError("raw_confidence must be numeric")
        calibrated = round(max(0.0, min(1.0, float(raw_confidence))), 4)
        return ConfidenceCalibration(
            raw_confidence=float(raw_confidence),
            calibrated_confidence=calibrated,
        )

    def detect_drift(
        self,
        baseline_scores: list[float],
        current_scores: list[float],
        threshold: float = 0.1,
    ) -> DriftReport:
        if threshold < 0:
            raise ValueError("threshold cannot be negative")
        if not baseline_scores or not current_scores:
            raise ValueError("baseline_scores and current_scores are required")
        baseline_average = self._average_score(baseline_scores, "baseline_scores")
        current_average = self._average_score(current_scores, "current_scores")
        drift_score = round(abs(current_average - baseline_average), 4)
        report = DriftReport(
            model_version=self.model_version,
            baseline_average_score=baseline_average,
            current_average_score=current_average,
            drift_score=drift_score,
            drift_detected=drift_score >= threshold,
            threshold=threshold,
        )
        self.ledger.append(
            DecisionEvent(
                stage="ml_signal_quality",
                input_id=self.model_version.identifier,
                output_id=self.model_version.identifier,
                reason="Drift report created",
                payload={
                    "event_type": MLEventType.ML_DRIFT_REPORT_CREATED.value,
                    "drift_detected": report.drift_detected,
                    "drift_score": report.drift_score,
                    "threshold": report.threshold,
                },
            )
        )
        return report

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

    def _average_score(self, scores: list[float], label: str) -> float:
        for score in scores:
            if not isinstance(score, (int, float)) or not 0 <= score <= 1:
                raise ValueError(f"{label} must contain scores between 0 and 1")
        return round(sum(scores) / len(scores), 4)

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

    def _emit_dataset_event(self, dataset: TrainingDataset, reason: str):
        self.ledger.append(
            DecisionEvent(
                stage="ml_signal_quality",
                input_id=dataset.model_version.identifier,
                output_id=dataset.model_version.identifier,
                reason=reason,
                payload={
                    "event_type": MLEventType.ML_TRAINING_DATASET_VALIDATED.value,
                    "model_version": dataset.model_version.identifier,
                    "example_count": len(dataset.examples),
                },
            )
        )
