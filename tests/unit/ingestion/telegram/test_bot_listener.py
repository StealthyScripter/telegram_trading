from datetime import datetime, timezone

from contracts.raw_message import RawMessage
from ingestion.telegram.bot_listener import TelegramBotListener
from signals.signal_store import SignalStore
from signals.telegram_bot_listener import TelegramBotListener as CompatibilityBotListener


def make_listener(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")

    return TelegramBotListener(
        store=SignalStore(path=str(tmp_path / "signals.json")),
        offset_path=str(tmp_path / "offset.json"),
    )


def test_compatibility_import_reexports_new_listener():
    assert CompatibilityBotListener is TelegramBotListener


def test_matching_chat_message_stored_and_convertible_to_raw_message(tmp_path, monkeypatch):
    listener = make_listener(tmp_path, monkeypatch)
    update = {
        "update_id": 10,
        "message": {
            "message_id": 99,
            "date": int(datetime.now(timezone.utc).timestamp()),
            "text": "BUY EURUSD SL 1.1300 TP 1.1400",
            "chat": {"id": 12345, "type": "private", "first_name": "Tester"},
        },
    }

    result = listener._handle_update(
        update=update,
        received_at=datetime.now(timezone.utc),
        elapsed_ms=12.5,
    )
    raw_message = listener.to_raw_message(update)

    assert result["saved"] is True
    assert isinstance(raw_message, RawMessage)
    assert raw_message.raw_text == "BUY EURUSD SL 1.1300 TP 1.1400"


def test_other_chat_and_empty_message_are_ignored(tmp_path, monkeypatch):
    listener = make_listener(tmp_path, monkeypatch)

    other_chat = {
        "message": {
            "message_id": 1,
            "date": int(datetime.now(timezone.utc).timestamp()),
            "text": "BUY EURUSD",
            "chat": {"id": 999},
        }
    }
    empty = {
        "message": {
            "message_id": 2,
            "date": int(datetime.now(timezone.utc).timestamp()),
            "text": " ",
            "chat": {"id": 12345},
        }
    }

    assert listener._handle_update(other_chat, datetime.now(timezone.utc), 1) is None
    assert listener._handle_update(empty, datetime.now(timezone.utc), 1) is None


def test_duplicate_message_ignored(tmp_path, monkeypatch):
    listener = make_listener(tmp_path, monkeypatch)
    update = {
        "message": {
            "message_id": 99,
            "date": int(datetime.now(timezone.utc).timestamp()),
            "text": "BUY EURUSD SL 1.1300 TP 1.1400",
            "chat": {"id": 12345, "first_name": "Tester"},
        }
    }

    first = listener._handle_update(update, datetime.now(timezone.utc), 1)
    second = listener._handle_update(update, datetime.now(timezone.utc), 1)

    assert first["saved"] is True
    assert second["saved"] is False
    assert second["reason"] == "duplicate"
