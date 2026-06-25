from datetime import datetime, timezone

from signals.signal_store import SignalStore


def test_save_raw_signal(tmp_path):
    store = SignalStore(path=str(tmp_path / "signals.json"))

    result = store.save_raw_signal(
        source="telegram_test",
        source_title="Telegram Test",
        chat_id="123",
        message_id="1",
        posted_at=datetime.now(timezone.utc),
        raw_text="BUY EURUSD SL 1.1300 TP 1.1400",
    )

    assert result["saved"] is True

    signals = store.all_signals()

    assert len(signals) == 1
    assert signals[0]["source"] == "telegram_test"
    assert signals[0]["raw_text"] == "BUY EURUSD SL 1.1300 TP 1.1400"
    assert signals[0]["parse_status"] == "UNPARSED"
    assert signals[0]["execution_status"] == "OBSERVE_ONLY"


def test_dedupes_same_source_and_message_id(tmp_path):
    store = SignalStore(path=str(tmp_path / "signals.json"))

    first = store.save_raw_signal(
        source="telegram_test",
        source_title="Telegram Test",
        chat_id="123",
        message_id="1",
        posted_at=datetime.now(timezone.utc),
        raw_text="BUY EURUSD",
    )

    second = store.save_raw_signal(
        source="telegram_test",
        source_title="Telegram Test",
        chat_id="123",
        message_id="1",
        posted_at=datetime.now(timezone.utc),
        raw_text="BUY EURUSD",
    )

    assert first["saved"] is True
    assert second["saved"] is False
    assert second["reason"] == "duplicate"
    assert len(store.all_signals()) == 1


def test_latest_returns_recent_signals(tmp_path):
    store = SignalStore(path=str(tmp_path / "signals.json"))

    for i in range(5):
        store.save_raw_signal(
            source="telegram_test",
            source_title="Telegram Test",
            chat_id="123",
            message_id=str(i),
            posted_at=datetime.now(timezone.utc),
            raw_text=f"Signal {i}",
        )

    latest = store.latest(limit=2)

    assert len(latest) == 2
    assert latest[0]["raw_text"] == "Signal 3"
    assert latest[1]["raw_text"] == "Signal 4"
