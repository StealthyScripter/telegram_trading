import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


class SignalStore:
    def __init__(self, path: str = "data/signals.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self._write({"signals": []})

    def _read(self) -> dict:
        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _write(self, data: dict):
        fd, temp_path = tempfile.mkstemp(
            dir=str(self.path.parent),
            prefix=".signals_",
            suffix=".json",
        )

        with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
            json.dump(data, temp_file, indent=2, default=str)

        os.replace(temp_path, self.path)

    def make_signal_id(self, source: str, message_id: str | int) -> str:
        return f"{source}:{message_id}"

    def exists(self, source: str, message_id: str | int) -> bool:
        signal_id = self.make_signal_id(source, message_id)

        return any(
            signal.get("signal_id") == signal_id
            for signal in self.all_signals()
        )

    def save_raw_signal(
        self,
        source: str,
        source_title: str | None,
        message_id: str | int,
        posted_at,
        raw_text: str,
        chat_id: str | int | None = None,
    ) -> dict:
        signal_id = self.make_signal_id(source, message_id)

        if self.exists(source, message_id):
            return {
                "saved": False,
                "reason": "duplicate",
                "signal_id": signal_id,
            }

        data = self._read()

        record = {
            "signal_id": signal_id,
            "source": source,
            "source_title": source_title,
            "chat_id": str(chat_id) if chat_id is not None else None,
            "message_id": str(message_id),
            "posted_at": posted_at.isoformat() if hasattr(posted_at, "isoformat") else str(posted_at),
            "received_at": datetime.now(timezone.utc).isoformat(),
            "raw_text": raw_text,
            "parse_status": "UNPARSED",
            "parsed_signal": None,
            "execution_status": "OBSERVE_ONLY",
        }

        data["signals"].append(record)
        self._write(data)

        return {
            "saved": True,
            "signal_id": signal_id,
            "record": record,
        }

    def all_signals(self):
        return self._read().get("signals", [])

    def latest(self, limit: int = 10):
        return self.all_signals()[-limit:]

    def update_signal(self, signal_id: str, updates: dict):
        data = self._read()

        for signal in data["signals"]:
            if signal["signal_id"] == signal_id:
                signal.update(updates)
                self._write(data)
                return signal

        raise ValueError(f"No signal found for signal_id: {signal_id}")
