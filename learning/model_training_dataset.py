from dataclasses import dataclass
from uuid import uuid4

from events.ledger import EventLedger
from events.models import DecisionEvent


@dataclass(frozen=True)
class TrainingExample:
    source: str
    features: dict
    label: str
    id: str = ""

    def __post_init__(self):
        if not self.id:
            object.__setattr__(self, "id", str(uuid4()))


class ModelTrainingDataset:
    def __init__(self, ledger: EventLedger | None = None):
        self.ledger = ledger or EventLedger()

    def from_events(self, events: list[dict]) -> list[TrainingExample]:
        examples = []
        for event in events:
            payload = event.get("payload") or {}
            source = payload.get("source") or payload.get("source_name")
            realized_r = payload.get("realized_r")
            if source is None or realized_r is None:
                continue
            label = "win" if float(realized_r) > 0 else "loss"
            example = TrainingExample(
                source=str(source),
                features={"realized_r": float(realized_r)},
                label=label,
            )
            examples.append(example)
            self._emit(example)
        return examples

    def refresh_from_events(self, events: list[dict]) -> list[TrainingExample]:
        return self.from_events(events)

    def _emit(self, example: TrainingExample):
        self.ledger.append(
            DecisionEvent(
                stage="learning",
                input_id=example.source,
                output_id=example.id,
                reason="Training example created",
                payload={
                    "event_type": "TRAINING_EXAMPLE_CREATED",
                    "source": example.source,
                    "features": example.features,
                    "label": example.label,
                },
            )
        )
