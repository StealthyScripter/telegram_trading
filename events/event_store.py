import json
import os
import tempfile
from pathlib import Path

from events.trade_event import TradeEvent


class EventStore:
    def __init__(self, path: str = "data/trade_events.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self._write({"events": []})

    def _read(self):
        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _write(self, data):
        fd, temp_path = tempfile.mkstemp(
            dir=str(self.path.parent),
            prefix=".trade_events_",
            suffix=".json",
        )

        with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
            json.dump(data, temp_file, indent=2, default=str)

        os.replace(temp_path, self.path)

    def append(self, event: TradeEvent):
        data = self._read()
        record = event.to_dict()
        data["events"].append(record)
        self._write(data)
        return record

    def all_events(self):
        return self._read()["events"]

    def find_by_signal_id(self, signal_id: str):
        return [
            event for event in self.all_events()
            if event.get("signal_id") == signal_id
        ]

    def find_by_trade_id(self, trade_id: str):
        return [
            event for event in self.all_events()
            if event.get("trade_id") == trade_id
        ]

    def latest(self, limit: int = 20):
        return self.all_events()[-limit:]
