import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from events.models import DecisionEvent


@dataclass(frozen=True)
class ReplayedTrace:
    trace_id: str
    events: list[dict]

    @property
    def stages(self) -> list[str]:
        return [event["stage"] for event in self.events]


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
        self._validate_record(record)
        if any(existing.get("event_id") == record["event_id"] for existing in data["events"]):
            raise ValueError(f"Duplicate event_id: {record['event_id']}")
        data["events"].append(record)
        self._write(data)
        return record

    def all_events(self) -> list[dict]:
        events = self._read()["events"]
        for event in events:
            self._validate_record(event)
        return events

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

    def replay_trace(
        self,
        trace_id: str,
        required_stages: list[str] | None = None,
    ) -> ReplayedTrace:
        events = [
            event for event in self.all_events()
            if event.get("trace_id") == trace_id
        ]
        if not events:
            raise ValueError(f"No events found for trace_id: {trace_id}")

        ordered = sorted(events, key=lambda event: event["created_at"])
        stages = [event["stage"] for event in ordered]
        for stage in required_stages or []:
            if stage not in stages:
                raise ValueError(f"Missing required stage: {stage}")

        return ReplayedTrace(trace_id=trace_id, events=ordered)

    def _validate_record(self, record: dict):
        required = ["event_id", "stage", "created_at"]
        missing = [field for field in required if not record.get(field)]
        if missing:
            raise ValueError(f"Malformed event missing: {', '.join(missing)}")
