from datetime import datetime, timezone

import pytest

from signals.signal_store import SignalStore
from signals.telegram_channel_client import TelegramChannelClient


class FakeChat:
    title = "Fake Signals"
    username = "fake_signals"


class FakeMessage:
    id = 123
    raw_text = "BUY EURUSD SL 1.1300 TP 1.1400"
    date = datetime.now(timezone.utc)
    chat_id = -100123

    async def get_chat(self):
        return FakeChat()


class EmptyMessage(FakeMessage):
    raw_text = "   "


@pytest.mark.asyncio
async def test_channel_client_handles_and_parses_message(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "abc")
    monkeypatch.setenv("TELEGRAM_PHONE", "+10000000000")

    store = SignalStore(path=str(tmp_path / "signals.json"))

    client = TelegramChannelClient(
        channels=["fake_signals"],
        store=store,
    )

    result = await client.handle_message(FakeMessage())

    assert result["saved"] is True

    signals = store.all_signals()

    assert len(signals) == 1
    assert signals[0]["source"] == "fake_signals"
    assert signals[0]["parse_status"] == "VALID_SIGNAL"
    assert signals[0]["execution_status"] == "READY_FOR_PAPER"
    assert signals[0]["parsed_signal"]["symbol"] == "EUR_USD"


@pytest.mark.asyncio
async def test_channel_client_dedupes_messages(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "abc")
    monkeypatch.setenv("TELEGRAM_PHONE", "+10000000000")

    store = SignalStore(path=str(tmp_path / "signals.json"))

    client = TelegramChannelClient(
        channels=["fake_signals"],
        store=store,
    )

    first = await client.handle_message(FakeMessage())
    second = await client.handle_message(FakeMessage())

    assert first["saved"] is True
    assert second["saved"] is False
    assert second["reason"] == "duplicate"
    assert len(store.all_signals()) == 1


@pytest.mark.asyncio
async def test_channel_client_ignores_empty_message(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "abc")
    monkeypatch.setenv("TELEGRAM_PHONE", "+10000000000")

    store = SignalStore(path=str(tmp_path / "signals.json"))

    client = TelegramChannelClient(
        channels=["fake_signals"],
        store=store,
    )

    result = await client.handle_message(EmptyMessage())

    assert result is None
    assert store.all_signals() == []
