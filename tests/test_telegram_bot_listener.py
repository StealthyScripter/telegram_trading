from datetime import datetime, timezone

from signals.signal_store import SignalStore
from signals.telegram_bot_listener import TelegramBotListener


def make_listener(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")

    store = SignalStore(path=str(tmp_path / "signals.json"))

    return TelegramBotListener(
        store=store,
        offset_path=str(tmp_path / "offset.json"),
    )


def test_bot_listener_stores_matching_chat_message(tmp_path, monkeypatch):
    listener = make_listener(tmp_path, monkeypatch)

    update = {
        "update_id": 10,
        "message": {
            "message_id": 99,
            "date": int(datetime.now(timezone.utc).timestamp()),
            "text": "BUY EURUSD SL 1.1300 TP 1.1400",
            "chat": {
                "id": 12345,
                "type": "private",
                "first_name": "Tester",
            },
        },
    }

    result = listener._handle_update(
        update=update,
        received_at=datetime.now(timezone.utc),
        elapsed_ms=12.5,
    )

    assert result["saved"] is True

    signals = listener.store.all_signals()

    assert len(signals) == 1
    assert signals[0]["raw_text"] == "BUY EURUSD SL 1.1300 TP 1.1400"
    assert signals[0]["chat_id"] == "12345"
    assert "latency_ms" in signals[0]


def test_bot_listener_ignores_other_chat(tmp_path, monkeypatch):
    listener = make_listener(tmp_path, monkeypatch)

    update = {
        "update_id": 10,
        "message": {
            "message_id": 99,
            "date": int(datetime.now(timezone.utc).timestamp()),
            "text": "BUY EURUSD",
            "chat": {
                "id": 99999,
                "type": "private",
                "first_name": "Other",
            },
        },
    }

    result = listener._handle_update(
        update=update,
        received_at=datetime.now(timezone.utc),
        elapsed_ms=12.5,
    )

    assert result is None
    assert listener.store.all_signals() == []


def test_bot_listener_dedupes_message(tmp_path, monkeypatch):
    listener = make_listener(tmp_path, monkeypatch)

    update = {
        "update_id": 10,
        "message": {
            "message_id": 99,
            "date": int(datetime.now(timezone.utc).timestamp()),
            "text": "BUY EURUSD",
            "chat": {
                "id": 12345,
                "type": "private",
                "first_name": "Tester",
            },
        },
    }

    first = listener._handle_update(
        update=update,
        received_at=datetime.now(timezone.utc),
        elapsed_ms=10,
    )

    second = listener._handle_update(
        update=update,
        received_at=datetime.now(timezone.utc),
        elapsed_ms=10,
    )

    assert first["saved"] is True
    assert second["saved"] is False
    assert second["reason"] == "duplicate"
    assert len(listener.store.all_signals()) == 1
