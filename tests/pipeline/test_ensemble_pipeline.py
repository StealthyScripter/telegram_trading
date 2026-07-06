from contracts.raw_message import RawMessage
from decision.ensemble import EnsembleDecisionEngine
from events.ledger import EventLedger
from orchestration.pipeline import Pipeline


def raw_message(source, text):
    return RawMessage(
        source=source,
        message_id=f"{source}-1",
        posted_at="2026-01-01T10:00:00+00:00",
        received_at="2026-01-01T10:00:01+00:00",
        raw_text=text,
    )


def test_ensemble_pipeline_approves_consensus(tmp_path):
    pipeline = Pipeline(ledger=EventLedger(path=str(tmp_path / "pipeline.json")))
    candidates = [
        pipeline.run(raw_message("alpha", "BUY EURUSD SL 1.0950 TP 1.1100")).trade_candidate,
        pipeline.run(raw_message("beta", "BUY EURUSD SL 1.0950 TP 1.1100")).trade_candidate,
    ]
    ensemble = EnsembleDecisionEngine(
        ledger=EventLedger(path=str(tmp_path / "ensemble.json"))
    )

    decision = ensemble.evaluate(candidates)

    assert decision.approved is True
    assert decision.candidate.symbol == "EUR_USD"
    assert ensemble.ledger.find_by_stage("ensemble")


def test_ensemble_pipeline_rejects_conflict(tmp_path):
    pipeline = Pipeline(ledger=EventLedger(path=str(tmp_path / "pipeline.json")))
    candidates = [
        pipeline.run(raw_message("alpha", "BUY EURUSD SL 1.0950 TP 1.1100")).trade_candidate,
        pipeline.run(raw_message("beta", "SELL EURUSD SL 1.1050 TP 1.0900")).trade_candidate,
    ]

    decision = EnsembleDecisionEngine(
        ledger=EventLedger(path=str(tmp_path / "ensemble.json"))
    ).evaluate(candidates)

    assert decision.approved is False
    assert decision.conflict.conflict_detected is True
