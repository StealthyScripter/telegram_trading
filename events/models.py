from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True)
class DecisionEvent:
    stage: str
    input_id: str | None
    output_id: str | None
    reason: str | None = None
    version: str = "1"
    payload: dict = field(default_factory=dict)
    trace_id: str | None = None
    correlation_id: str | None = None
    event_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self):
        if not self.stage:
            raise ValueError("DecisionEvent.stage is required")
        object.__setattr__(self, "payload", deepcopy(self.payload))

    def to_dict(self) -> dict:
        return deepcopy(asdict(self))
