import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from telethon import TelegramClient, events

from signals.signal_processor import SignalProcessor
from signals.signal_store import SignalStore

load_dotenv()


class TelegramChannelClient:
    def __init__(
        self,
        channels: list[str | int],
        store: SignalStore | None = None,
    ):
        self.api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.phone = os.getenv("TELEGRAM_PHONE")
        self.session_name = os.getenv(
            "TELEGRAM_SESSION_NAME",
            "telegram_signal_session",
        )

        if not self.api_id:
            raise ValueError("Missing TELEGRAM_API_ID in .env")

        if not self.api_hash:
            raise ValueError("Missing TELEGRAM_API_HASH in .env")

        if not self.phone:
            raise ValueError("Missing TELEGRAM_PHONE in .env")

        self.channels = channels
        self.store = store or SignalStore()
        self.processor = SignalProcessor()

        self.client = TelegramClient(
            self.session_name,
            self.api_id,
            self.api_hash,
        )

    async def connect(self):
        await self.client.start(phone=self.phone)

    async def disconnect(self):
        await self.client.disconnect()

    async def import_history(
        self,
        channel: str | int,
        limit: int = 100,
    ) -> list[dict]:
        await self.connect()

        saved = []

        async for message in self.client.iter_messages(channel, limit=limit):
            result = await self.handle_message(
                message=message,
                source_override=str(channel),
            )

            if result:
                saved.append(result)

        await self.disconnect()
        return saved

    async def listen_forever(self):
        await self.connect()

        @self.client.on(events.NewMessage(chats=self.channels))
        async def handler(event):
            result = await self.handle_message(
                message=event.message,
                source_override=None,
            )

            if result and result.get("saved"):
                record = result["record"]
                print("=" * 60)
                print(f"Saved signal: {record['signal_id']}")
                print(f"Source: {record['source']}")
                print(f"Posted: {record['posted_at']}")
                print(f"Parse: {record['parse_status']}")
                print(record["raw_text"])
                print("=" * 60)

        print("Telethon channel listener started")
        print(f"Watching channels: {self.channels}")

        await self.client.run_until_disconnected()

    async def handle_message(
        self,
        message,
        source_override: str | None = None,
    ):
        raw_text = message.raw_text or ""

        if not raw_text.strip():
            return None

        chat = await message.get_chat()

        source_title = getattr(chat, "title", None)
        username = getattr(chat, "username", None)
        chat_id = getattr(message, "chat_id", None)

        source = source_override or username or str(chat_id)
        posted_at = message.date or datetime.now(timezone.utc)

        result = self.store.save_raw_signal(
            source=str(source),
            source_title=source_title,
            chat_id=chat_id,
            message_id=message.id,
            posted_at=posted_at,
            raw_text=raw_text,
        )

        if not result.get("saved"):
            return result

        processed = self.processor.process_raw_signal(result["record"])

        self.store.update_signal(
            signal_id=processed["signal_id"],
            updates={
                "parse_status": processed["parse_status"],
                "parsed_signal": processed["parsed_signal"],
                "execution_status": processed["execution_status"],
            },
        )

        result["record"] = processed
        return result
