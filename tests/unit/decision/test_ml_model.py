import inspect

from contracts.parsed_signal import ParsedSignal, ParsedSignalStatus
from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus
from decision import ml_model as ml_module
import pytest

from decision.ml_model import (
    MLEventType,
    MLModel,
    ModelDecisionContext,
    ModelInputFeatures,
    ModelVersion,
    TrainingDataset,
    TrainingExample,
)
from events.ledger import EventLedger


def parsed_signal(**overrides):
    data = {
        "raw_message_id": "raw-1",
        "source": "telegram_alpha",
        "status": ParsedSignalStatus.VALID_SIGNAL,
        "symbol": "EUR_USD",
        "action": "buy",
        "entry_price": "1.1000",
        "stop_loss": "1.0950",
        "take_profits": ["1.1100", "1.1200"],
    }
    data.update(overrides)
    return ParsedSignal(**data)


def candidate(**overrides):
    data = {
        "parsed_signal_id": "parsed-1",
        "source": "telegram_alpha",
        "status": TradeCandidateStatus.APPROVED_FOR_RISK,
        "symbol": "EUR_USD",
        "action": "buy",
        "entry_price": "1.1000",
        "stop_loss": "1.0950",
        "take_profits": ["1.1100"],
    }
    data.update(overrides)
    return TradeCandidate(**data)


def model(tmp_path):
    return MLModel(ledger=EventLedger(path=str(tmp_path / "ml_ledger.json")))


def test_feature_extraction_from_parsed_signal(tmp_path):
    features = model(tmp_path).extract_features(
        parsed_signal(),
        ModelDecisionContext(source_score=90),
    )

    assert features.has_entry is True
    assert features.has_stop_loss is True
    assert features.take_profit_count == 2
    assert round(features.reward_risk_ratio, 2) == 2.0
    assert features.source_score == 90
    assert features.parse_status == "VALID_SIGNAL"


def test_high_quality_signal_score(tmp_path):
    prediction = model(tmp_path).score(
        parsed_signal(),
        ModelDecisionContext(source_score=90, minimum_score=0.5),
    )

    assert prediction.approved is True
    assert prediction.score >= 0.5
    assert prediction.model_version.identifier


def test_poor_signal_score_is_advisory_rejection(tmp_path):
    poor = ParsedSignal(
        raw_message_id="raw-1",
        source="telegram_alpha",
        status=ParsedSignalStatus.PARTIAL_SIGNAL,
        symbol="EUR_USD",
        action="buy",
        take_profits=[],
        reason="missing stop loss",
    )

    prediction = model(tmp_path).score(
        poor,
        ModelDecisionContext(minimum_score=0.5),
    )

    assert prediction.approved is False
    assert prediction.reason == "Signal quality below threshold"


def test_missing_stop_loss_reduces_score(tmp_path):
    poor = candidate(stop_loss=None)

    prediction = model(tmp_path).score(
        poor,
        ModelDecisionContext(minimum_score=0.5),
    )

    assert prediction.score < 0.5


def test_model_version_present_and_customizable(tmp_path):
    custom = MLModel(
        model_version=ModelVersion(name="test_model", version="2"),
        ledger=EventLedger(path=str(tmp_path / "ml_ledger.json")),
    )

    prediction = custom.score(parsed_signal())

    assert prediction.model_version.identifier == "test_model:2"


def test_prediction_is_deterministic(tmp_path):
    signal = parsed_signal()
    first = model(tmp_path).score(signal).score
    second = model(tmp_path).score(signal).score

    assert first == second


def test_ledger_events_emitted(tmp_path):
    quality_model = model(tmp_path)

    quality_model.score(parsed_signal())

    event_types = [
        event["payload"]["event_type"]
        for event in quality_model.ledger.all_events()
    ]

    assert MLEventType.ML_MODEL_VERSION_USED.value in event_types
    assert MLEventType.ML_SIGNAL_SCORED.value in event_types


def test_ml_model_has_no_execution_or_broker_imports():
    source = inspect.getsource(ml_module)

    for forbidden in ["TradeExecutor", "BrokerFactory", "OandaBroker", "PaperBroker"]:
        assert forbidden not in source


def test_feature_schema_validation_accepts_valid_features(tmp_path):
    quality_model = model(tmp_path)
    features = quality_model.extract_features(parsed_signal())

    quality_model.validate_features(features)


def test_missing_required_feature_type_fails_safely(tmp_path):
    features = ModelInputFeatures(
        has_entry="yes",
        has_stop_loss=True,
        take_profit_count=1,
        stop_distance=0.005,
        reward_risk_ratio=2.0,
        source_score=90,
        symbol="EUR_USD",
        action="buy",
        parse_status="VALID_SIGNAL",
    )

    with pytest.raises(ValueError, match="has_entry"):
        model(tmp_path).validate_features(features)


def test_invalid_feature_value_fails_safely(tmp_path):
    features = ModelInputFeatures(
        has_entry=True,
        has_stop_loss=True,
        take_profit_count=-1,
        stop_distance=0.005,
        reward_risk_ratio=2.0,
        source_score=90,
        symbol="EUR_USD",
        action="buy",
        parse_status="VALID_SIGNAL",
    )

    with pytest.raises(ValueError, match="take_profit_count"):
        model(tmp_path).validate_features(features)


def test_dataset_validation_accepts_valid_dataset(tmp_path):
    quality_model = model(tmp_path)
    dataset = TrainingDataset(
        examples=(
            TrainingExample(features=quality_model.extract_features(parsed_signal()), label=1.0),
        ),
        model_version=quality_model.model_version,
    )

    quality_model.validate_dataset(dataset)

    assert quality_model.ledger.latest(1)[0]["payload"]["event_type"] == MLEventType.ML_TRAINING_DATASET_VALIDATED.value


def test_dataset_validation_rejects_invalid_dataset(tmp_path):
    quality_model = model(tmp_path)
    dataset = TrainingDataset(examples=(), model_version=quality_model.model_version)

    with pytest.raises(ValueError, match="cannot be empty"):
        quality_model.validate_dataset(dataset)


def test_offline_training_report_is_deterministic(tmp_path):
    quality_model = model(tmp_path)
    dataset = TrainingDataset(
        examples=(
            TrainingExample(features=quality_model.extract_features(parsed_signal()), label=1.0),
            TrainingExample(features=quality_model.extract_features(candidate(stop_loss=None)), label=0.0),
        ),
        model_version=quality_model.model_version,
    )

    first = quality_model.train_offline(dataset)
    second = quality_model.train_offline(dataset)

    assert first == second
    assert first.model_version.identifier == quality_model.model_version.identifier
    assert first.example_count == 2


def test_shadow_prediction_is_advisory_only(tmp_path):
    shadow = model(tmp_path).shadow_predict(parsed_signal())

    assert shadow.advisory_only is True
    assert shadow.affects_execution is False
    assert shadow.metadata["model_version"] == shadow.prediction.model_version.identifier


def test_drift_detector_emits_advisory_report_only(tmp_path):
    quality_model = model(tmp_path)

    report = quality_model.detect_drift(
        baseline_scores=[0.8, 0.9],
        current_scores=[0.4, 0.5],
        threshold=0.1,
    )

    assert report.drift_detected is True
    assert report.drift_score == 0.4
    assert quality_model.ledger.latest(1)[0]["payload"]["event_type"] == MLEventType.ML_DRIFT_REPORT_CREATED.value


def test_confidence_calibration_is_bounded_and_deterministic(tmp_path):
    quality_model = model(tmp_path)

    first = quality_model.calibrate_confidence(1.5)
    second = quality_model.calibrate_confidence(1.5)

    assert first == second
    assert first.calibrated_confidence == 1.0
