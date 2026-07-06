from decision.strategy_fusion import SignalSourceType, StrategyFusionEngine, StrategySignal
from events.ledger import EventLedger
from ingestion.manual import ManualSignalIngestor
from ingestion.webhooks import WebhookSignalIngestor
from orchestration.pipeline import Pipeline


def test_strategy_fusion_pipeline_approves_agreement(tmp_path):
    pipeline = Pipeline(ledger=EventLedger(path=str(tmp_path / "pipeline.json")))
    manual = ManualSignalIngestor().ingest(
        "BUY EURUSD SL 1.0950 TP 1.1100",
        source="manual",
        message_id="manual-1",
    )
    webhook = WebhookSignalIngestor().ingest(
        {
            "source": "webhook",
            "id": "webhook-1",
            "message": "BUY EURUSD SL 1.0950 TP 1.1100",
        }
    )
    candidates = [
        pipeline.run(manual).trade_candidate,
        pipeline.run(webhook).trade_candidate,
    ]
    fusion = StrategyFusionEngine(ledger=EventLedger(path=str(tmp_path / "fusion.json")))

    decision = fusion.fuse(
        [
            StrategySignal(SignalSourceType.MANUAL, "manual", candidates[0]),
            StrategySignal(SignalSourceType.WEBHOOK, "webhook", candidates[1]),
        ]
    )

    assert decision.approved is True
    assert decision.candidate.symbol == "EUR_USD"
    assert fusion.ledger.find_by_stage("strategy_fusion")


def test_strategy_fusion_pipeline_rejects_disagreement(tmp_path):
    pipeline = Pipeline(ledger=EventLedger(path=str(tmp_path / "pipeline.json")))
    first = ManualSignalIngestor().ingest(
        "BUY EURUSD SL 1.0950 TP 1.1100",
        source="manual",
        message_id="manual-1",
    )
    second = WebhookSignalIngestor().ingest(
        {
            "source": "webhook",
            "id": "webhook-1",
            "message": "SELL EURUSD SL 1.1050 TP 1.0900",
        }
    )
    fusion = StrategyFusionEngine(ledger=EventLedger(path=str(tmp_path / "fusion.json")))

    decision = fusion.fuse(
        [
            StrategySignal(SignalSourceType.MANUAL, "manual", pipeline.run(first).trade_candidate),
            StrategySignal(SignalSourceType.WEBHOOK, "webhook", pipeline.run(second).trade_candidate),
        ]
    )

    assert decision.approved is False
