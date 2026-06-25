from signals.signal_processor import SignalProcessor


def test_processor_marks_valid_signal_ready_for_paper():
    processor = SignalProcessor()

    raw = {
        "signal_id": "telegram:1",
        "raw_text": "BUY EURUSD SL 1.1300 TP 1.1400",
    }

    result = processor.process_raw_signal(raw)

    assert result["parse_status"] == "VALID_SIGNAL"
    assert result["execution_status"] == "READY_FOR_PAPER"
    assert result["parsed_signal"]["symbol"] == "EUR_USD"


def test_processor_marks_commentary_observe_only():
    processor = SignalProcessor()

    raw = {
        "signal_id": "telegram:2",
        "raw_text": "London session is slow today",
    }

    result = processor.process_raw_signal(raw)

    assert result["parse_status"] == "COMMENTARY_ONLY"
    assert result["execution_status"] == "OBSERVE_ONLY"
