import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from contracts.raw_message import RawMessage

import requests
from dotenv import load_dotenv

from storage.signal_store import SignalStore

load_dotenv()


class TelegramBotListener:
    def __init__(
        self,
        token: str | None = None,
        chat_id: str | None = None,
        store: SignalStore | None = None,
        offset_path: str = "data/telegram_bot_offset.json",
    ):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = str(chat_id or os.getenv("TELEGRAM_CHAT_ID") or "")
        self.store = store or SignalStore()
        self.offset_path = Path(offset_path)

        if not self.token:
            raise ValueError("Missing TELEGRAM_BOT_TOKEN in .env")

        if not self.chat_id:
            raise ValueError("Missing TELEGRAM_CHAT_ID in .env")

        self.base_url = f"https://api.telegram.org/bot{self.token}"

        self.offset_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_offset(self) -> int | None:
        if not self.offset_path.exists():
            return None

        with self.offset_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return data.get("offset")

    def _set_offset(self, offset: int):
        with self.offset_path.open("w", encoding="utf-8") as file:
            json.dump({"offset": offset}, file, indent=2)

    def delete_webhook(self):
        response = requests.post(
            f"{self.base_url}/deleteWebhook",
            timeout=20,
        )
        data = response.json()

        if not data.get("ok"):
            raise RuntimeError(f"deleteWebhook failed: {data}")

        return data

    def get_me(self):
        response = requests.get(
            f"{self.base_url}/getMe",
            timeout=20,
        )
        data = response.json()

        if not data.get("ok"):
            raise RuntimeError(f"getMe failed: {data}")

        return data["result"]

    def poll_once(self, timeout: int = 30):
        params = {
            "timeout": timeout,
            "limit": 100,
            "allowed_updates": json.dumps(["message", "channel_post"]),
        }

        offset = self._get_offset()
        if offset is not None:
            params["offset"] = offset

        started_at = time.time()

        response = requests.get(
            f"{self.base_url}/getUpdates",
            params=params,
            timeout=timeout + 10,
        )

        received_at = datetime.now(timezone.utc)
        elapsed_ms = round((time.time() - started_at) * 1000, 2)

        data = response.json()

        if not data.get("ok"):
            raise RuntimeError(f"getUpdates failed: {data}")

        saved = []

        for update in data.get("result", []):
            update_id = update["update_id"]
            self._set_offset(update_id + 1)

            result = self._handle_update(
                update=update,
                received_at=received_at,
                elapsed_ms=elapsed_ms,
            )

            if result:
                saved.append(result)

        return saved

    def listen_forever(self, timeout: int = 30):
        print("Telegram bot listener started")
        print(f"Listening for chat_id: {self.chat_id}")
        print("Send a message to your bot/group now...")

        self.delete_webhook()
        bot = self.get_me()
        print(f"Connected bot: @{bot.get('username')}")

        while True:
            saved = self.poll_once(timeout=timeout)

            for item in saved:
                record = item.get("record", {})
                print("=" * 60)
                print(f"Saved: {item.get('signal_id')}")
                print(f"Source: {record.get('source')}")
                print(f"Posted at: {record.get('posted_at')}")
                print(f"Received at: {record.get('received_at')}")
                print(f"Latency ms: {record.get('latency_ms')}")
                print(record.get("raw_text"))
                print("=" * 60)

    def _handle_update(self, update: dict, received_at: datetime, elapsed_ms: float):
        message = update.get("message") or update.get("channel_post")

        if not message:
            return None

        chat = message.get("chat", {})
        actual_chat_id = str(chat.get("id"))

        if actual_chat_id != self.chat_id:
            return None

        raw_text = message.get("text") or message.get("caption") or ""

        if not raw_text.strip():
            return None

        message_id = message.get("message_id")
        message_timestamp = message.get("date")
        posted_at = datetime.fromtimestamp(message_timestamp, tz=timezone.utc)

        latency_ms = round(
            (received_at - posted_at).total_seconds() * 1000,
            2,
        )

        source = (
            chat.get("username")
            or chat.get("title")
            or chat.get("first_name")
            or actual_chat_id
        )

        result = self.store.save_raw_signal(
            source=str(source),
            source_title=chat.get("title") or chat.get("first_name"),
            chat_id=actual_chat_id,
            message_id=message_id,
            posted_at=posted_at,
            raw_text=raw_text,
        )

        if result.get("saved") and "record" in result:
            self.store.update_signal(
                signal_id=result["signal_id"],
                updates={
                    "latency_ms": latency_ms,
                    "poll_elapsed_ms": elapsed_ms,
                },
            )

            result["record"] = self.store.all_signals()[-1]

        return result

    def to_raw_message(self, update: dict, received_at: datetime | None = None):
        message = update.get("message") or update.get("channel_post")

        if not message:
            return None

        chat = message.get("chat", {})
        actual_chat_id = str(chat.get("id"))

        if actual_chat_id != self.chat_id:
            return None

        raw_text = message.get("text") or message.get("caption") or ""

        if not raw_text.strip():
            return None

        posted_at = datetime.fromtimestamp(
            message.get("date"),
            tz=timezone.utc,
        )
        received = received_at or datetime.now(timezone.utc)
        source = (
            chat.get("username")
            or chat.get("title")
            or chat.get("first_name")
            or actual_chat_id
        )

        return RawMessage(
            source=str(source),
            source_type="telegram_bot",
            source_title=chat.get("title") or chat.get("first_name"),
            chat_id=actual_chat_id,
            message_id=str(message.get("message_id")),
            posted_at=posted_at.isoformat(),
            received_at=received.isoformat(),
            raw_text=raw_text,
        )

    def _rewrite_signal_with_latency(self, updated_record: dict):
        data = {"signals": self.store.all_signals()}

        for index, signal in enumerate(data["signals"]):
            if signal["signal_id"] == updated_record["signal_id"]:
                data["signals"][index] = updated_record
                break

        self.store._write(data)
