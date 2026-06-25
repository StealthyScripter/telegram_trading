from datetime import datetime, timezone

import pytest

from signals.signal_store import SignalStore
from signals.telegram_listener import TelegramSignalListener


class FakeChat:
    title = "Fake Signal Channel"
    username = "fake_signal_channel"


class FakeEvent:
    id = 99
    raw_text = "BUY EURUSD SL 1.1300 TP 1.1400"
    date = datetime.now(timezone.utc)
    chat_id = -100123456789

    async def get_chat(self):
        return FakeChat()


@pytest.mark.asyncio
async def test_telegram_listener_handles_event(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "abc")
    monkeypatch.setenv("TELEGRAM_PHONE", "+10000000000")

    store = SignalStore(path=str(tmp_path / "signals.json"))

    listener = TelegramSignalListener(
        channels=["fake_signal_channel"],
        store=store,
    )

    result = await listener.handle_event(FakeEvent())

    assert result["saved"] is True

    signals = store.all_signals()

    assert len(signals) == 1
    assert signals[0]["source"] == "fake_signal_channel"
    assert signals[0]["message_id"] == "99"
    assert signals[0]["raw_text"] == "BUY EURUSD SL 1.1300 TP 1.1400"


@pytest.mark.asyncio
async def test_telegram_listener_ignores_empty_message(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "abc")
    monkeypatch.setenv("TELEGRAM_PHONE", "+10000000000")

    class EmptyEvent(FakeEvent):
        raw_text = "   "

    store = SignalStore(path=str(tmp_path / "signals.json"))

    listener = TelegramSignalListener(
        channels=["fake_signal_channel"],
        store=store,
    )

    result = await listener.handle_event(EmptyEvent())

    assert result is None
    assert store.all_signals() == []
    