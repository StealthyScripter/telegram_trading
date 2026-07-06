from contracts.raw_message import RawMessage
from decision.ml_model import MLModel, ModelDecisionContext
from events.ledger import EventLedger
from orchestration.pipeline import Pipeline


def raw_message(text):
    return RawMessage(
        source="telegram_alpha",
        message_id="1",
        posted_at="2026-01-01T10:00:00+00:00",
        received_at="2026-01-01T10:00:01+00:00",
        raw_text=text,
    )


def test_ml_pipeline_scores_candidate_without_execution(tmp_path):
    pipeline = Pipeline(ledger=EventLedger(path=str(tmp_path / "pipeline.json")))
    result = pipeline.run(raw_message("BUY EURUSD @ 1.1000 SL 1.0950 TP 1.1100"))
    quality_model = MLModel(ledger=EventLedger(path=str(tmp_path / "ml.json")))

    prediction = quality_model.score(
        result.trade_candidate,
        ModelDecisionContext(source_score=85, minimum_score=0.5),
    )

    assert prediction.approved is True
    assert result.execution_result is None
    assert quality_model.ledger.find_by_stage("ml_signal_quality")


def test_ml_pipeline_rejects_poor_candidate_advisory_only(tmp_path):
    pipeline = Pipeline(ledger=EventLedger(path=str(tmp_path / "pipeline.json")))
    result = pipeline.run(raw_message("BUY EURUSD"))
    quality_model = MLModel(ledger=EventLedger(path=str(tmp_path / "ml.json")))

    prediction = quality_model.score(
        result.trade_candidate,
        ModelDecisionContext(minimum_score=0.5),
    )

    assert prediction.approved is False
    assert result.execution_result is None
