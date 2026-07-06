import json
import os
import tempfile
from pathlib import Path

from events.models import DecisionEvent


class EventLedger:
    def __init__(self, path: str = "data/decision_events.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self._write({"events": []})

    def _read(self) -> dict:
        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _write(self, data: dict):
        fd, temp_path = tempfile.mkstemp(
            dir=str(self.path.parent),
            prefix=".decision_events_",
            suffix=".json",
        )

        with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
            json.dump(data, temp_file, indent=2, default=str)

        os.replace(temp_path, self.path)

    def append(self, event: DecisionEvent) -> dict:
        data = self._read()
        record = event.to_dict()
        data["events"].append(record)
        self._write(data)
        return record

    def all_events(self) -> list[dict]:
        return self._read()["events"]

    def find_by_input_id(self, input_id: str) -> list[dict]:
        return [
            event for event in self.all_events()
            if event.get("input_id") == input_id
        ]

    def find_by_output_id(self, output_id: str) -> list[dict]:
        return [
            event for event in self.all_events()
            if event.get("output_id") == output_id
        ]

    def find_by_stage(self, stage: str) -> list[dict]:
        return [
            event for event in self.all_events()
            if event.get("stage") == stage
        ]

    def latest(self, limit: int = 20) -> list[dict]:
        return self.all_events()[-limit:]
