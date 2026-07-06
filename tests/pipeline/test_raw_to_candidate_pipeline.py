from contracts.raw_message import RawMessage
from contracts.trade_candidate import TradeCandidateStatus
from events.ledger import EventLedger
from orchestration.pipeline import Pipeline


def make_raw_message(text: str) -> RawMessage:
    return RawMessage(
        source="telegram_test",
        message_id="1",
        posted_at="2026-01-01T10:00:00+00:00",
        received_at="2026-01-01T10:00:01+00:00",
        raw_text=text,
    )


def test_raw_message_to_trade_candidate_pipeline(tmp_path):
    ledger = EventLedger(path=str(tmp_path / "ledger.json"))
    pipeline = Pipeline(ledger=ledger)

    result = pipeline.run(make_raw_message("BUY EURUSD SL 1.1300 TP 1.1400"))

    assert result.trade_candidate.status == TradeCandidateStatus.APPROVED_FOR_RISK
    assert result.execution_result is None
    assert [event["stage"] for event in ledger.all_events()] == [
        "parsing",
        "decision",
    ]


def test_commentary_message_creates_non_executable_candidate(tmp_path):
    ledger = EventLedger(path=str(tmp_path / "ledger.json"))
    pipeline = Pipeline(ledger=ledger)

    result = pipeline.run(make_raw_message("London session is slow today"))

    assert result.trade_candidate.status == TradeCandidateStatus.OBSERVE_ONLY
    assert len(ledger.find_by_stage("decision")) == 1
