import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from telethon import TelegramClient, events

from contracts.raw_message import RawMessage
from storage.signal_store import SignalStore

load_dotenv()


class TelegramSignalListener:
    def __init__(
        self,
        channels: list[str | int],
        store: SignalStore | None = None,
    ):
        self.api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.phone = os.getenv("TELEGRAM_PHONE")
        self.session_name = os.getenv("TELEGRAM_SESSION_NAME", "telegram_signal_session")

        if not self.api_id:
            raise ValueError("Missing TELEGRAM_API_ID in .env")

        if not self.api_hash:
            raise ValueError("Missing TELEGRAM_API_HASH in .env")

        if not self.phone:
            raise ValueError("Missing TELEGRAM_PHONE in .env")

        self.channels = channels
        self.store = store or SignalStore()

        self.client = TelegramClient(
            self.session_name,
            self.api_id,
            self.api_hash,
        )

    async def start(self):
        await self.client.start(phone=self.phone)

        @self.client.on(events.NewMessage(chats=self.channels))
        async def handler(event):
            await self.handle_event(event)

        print("Telegram listener started")
        print(f"Watching channels: {self.channels}")

        await self.client.run_until_disconnected()

    async def handle_event(self, event):
        raw_text = event.raw_text or ""

        if not raw_text.strip():
            return None

        chat = await event.get_chat()

        source_title = getattr(chat, "title", None)
        username = getattr(chat, "username", None)
        chat_id = getattr(event, "chat_id", None)

        source = username or str(chat_id)

        result = self.store.save_raw_signal(
            source=source,
            source_title=source_title,
            chat_id=chat_id,
            message_id=event.id,
            posted_at=event.date,
            raw_text=raw_text,
        )

        if result["saved"]:
            print(f"Saved signal: {result['signal_id']}")
            print(raw_text[:250])
        else:
            print(f"Skipped duplicate: {result['signal_id']}")

        return result

    async def to_raw_message(self, event):
        raw_text = event.raw_text or ""

        if not raw_text.strip():
            return None

        chat = await event.get_chat()

        source_title = getattr(chat, "title", None)
        username = getattr(chat, "username", None)
        chat_id = getattr(event, "chat_id", None)
        source = username or str(chat_id)

        return RawMessage(
            source=source,
            source_type="telegram",
            source_title=source_title,
            chat_id=str(chat_id) if chat_id is not None else None,
            message_id=str(event.id),
            posted_at=event.date.isoformat(),
            received_at=datetime.now(timezone.utc).isoformat(),
            raw_text=raw_text,
        )
