from contracts.parsed_signal import ParsedSignalStatus
from contracts.raw_message import RawMessage
from parsing.parser import SignalParser
from signals.signal_parser import SignalParser as CompatibilitySignalParser


def make_raw_message(text: str) -> RawMessage:
    return RawMessage(
        source="telegram_test",
        message_id="1",
        posted_at="2026-01-01T10:00:00+00:00",
        received_at="2026-01-01T10:00:01+00:00",
        raw_text=text,
    )


def test_parse_raw_message_returns_contract():
    parser = SignalParser()

    parsed = parser.parse_raw_message(
        make_raw_message("BUY EURUSD SL 1.1300 TP 1.1400")
    )

    assert parsed.status == ParsedSignalStatus.VALID_SIGNAL
    assert parsed.symbol == "EUR_USD"
    assert parsed.action == "buy"
    assert parsed.take_profits == ["1.1400"]


def test_old_signal_parser_import_reexports_new_parser():
    assert CompatibilitySignalParser is SignalParser
