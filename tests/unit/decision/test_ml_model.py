import inspect

from contracts.parsed_signal import ParsedSignal, ParsedSignalStatus
from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus
from decision import ml_model as ml_module
from decision.ml_model import MLEventType, MLModel, ModelDecisionContext, ModelVersion
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
