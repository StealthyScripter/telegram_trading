from contracts.raw_message import RawMessage
from events.ledger import EventLedger
from orchestration.backtest_pipeline import BacktestPipeline
from orchestration.pipeline import Pipeline


def historical_message(message_id, text):
    return RawMessage(
        source="history_alpha",
        message_id=str(message_id),
        posted_at="2026-01-01T10:00:00+00:00",
        received_at="2026-01-01T10:00:01+00:00",
        raw_text=text,
    )


def test_historical_signal_replay_valid_and_commentary(tmp_path):
    pipeline = Pipeline(ledger=EventLedger(path=str(tmp_path / "pipeline.json")))
    backtest = BacktestPipeline(pipeline=pipeline)
    messages = [
        historical_message(1, "BUY EURUSD SL 1.0950 TP 1.1100"),
        historical_message(2, "London session is slow today"),
        historical_message(3, "BUY EURUSD"),
    ]

    results = [backtest.replay_raw_message(message) for message in messages]

    assert results[0].simulated_result["status"] == "SIMULATED"
    assert results[1].simulated_result is None
    assert results[2].simulated_result is None
    assert results[0].trade_candidate.symbol == "EUR_USD"
