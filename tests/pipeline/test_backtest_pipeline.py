from contracts.raw_message import RawMessage
from contracts.trade_candidate import TradeCandidateStatus
from events.ledger import EventLedger
from orchestration.backtest_pipeline import BacktestPipeline
from orchestration.pipeline import Pipeline


def make_raw_message(text: str) -> RawMessage:
    return RawMessage(
        source="telegram_test",
        message_id="1",
        posted_at="2026-01-01T10:00:00+00:00",
        received_at="2026-01-01T10:00:01+00:00",
        raw_text=text,
    )


def test_backtest_pipeline_simulates_valid_raw_message(tmp_path):
    pipeline = Pipeline(ledger=EventLedger(path=str(tmp_path / "ledger.json")))
    result = BacktestPipeline(pipeline=pipeline).replay_raw_message(
        make_raw_message("BUY EURUSD SL 1.1300 TP 1.1400")
    )

    assert result.trade_candidate.status == TradeCandidateStatus.APPROVED_FOR_RISK
    assert result.simulated_result["status"] == "SIMULATED"


def test_backtest_pipeline_skips_observe_only_message(tmp_path):
    pipeline = Pipeline(ledger=EventLedger(path=str(tmp_path / "ledger.json")))
    result = BacktestPipeline(pipeline=pipeline).replay_raw_message(
        make_raw_message("London session is slow today")
    )

    assert result.trade_candidate.status == TradeCandidateStatus.OBSERVE_ONLY
    assert result.simulated_result is None
