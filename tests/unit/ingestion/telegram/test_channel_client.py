from datetime import datetime, timezone

import pytest

from contracts.raw_message import RawMessage
from ingestion.telegram.channel_client import TelegramChannelClient
from signals.signal_store import SignalStore
from signals.telegram_channel_client import TelegramChannelClient as CompatibilityClient


class FakeChat:
    title = "Signals"
    username = "signals"


class FakeMessage:
    id = 7
    chat_id = 123
    raw_text = "BUY EURUSD SL 1.1300 TP 1.1400"
    date = datetime(2026, 1, 1, tzinfo=timezone.utc)

    async def get_chat(self):
        return FakeChat()


@pytest.mark.asyncio
async def test_channel_client_handles_message_and_raw_message(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_API_ID", "1")
    monkeypatch.setenv("TELEGRAM_API_HASH", "hash")
    monkeypatch.setenv("TELEGRAM_PHONE", "+10000000000")

    client = TelegramChannelClient(
        channels=["signals"],
        store=SignalStore(path=str(tmp_path / "signals.json")),
    )

    result = await client.handle_message(FakeMessage())
    raw_message = await client.to_raw_message(FakeMessage())

    assert result["saved"] is True
    assert result["record"]["parse_status"] == "VALID_SIGNAL"
    assert isinstance(raw_message, RawMessage)


def test_channel_client_compatibility_import():
    assert CompatibilityClient is TelegramChannelClient
