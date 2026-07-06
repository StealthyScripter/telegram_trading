import json

import pytest

from events.ledger import EventLedger
from events.models import DecisionEvent


def test_event_append_read_ordering(tmp_path):
    ledger = EventLedger(path=str(tmp_path / "events.json"))
    first = ledger.append(DecisionEvent(stage="parsing", input_id="raw", output_id="parsed"))
    second = ledger.append(DecisionEvent(stage="decision", input_id="parsed", output_id="candidate"))

    events = ledger.all_events()

    assert [event["event_id"] for event in events] == [
        first["event_id"],
        second["event_id"],
    ]


def test_trace_id_propagates_and_replays(tmp_path):
    ledger = EventLedger(path=str(tmp_path / "events.json"))
    ledger.append(DecisionEvent(stage="parsing", input_id="raw", output_id="parsed", trace_id="trace-1"))
    ledger.append(DecisionEvent(stage="decision", input_id="parsed", output_id="candidate", trace_id="trace-1"))

    trace = ledger.replay_trace("trace-1", required_stages=["parsing", "decision"])

    assert trace.stages == ["parsing", "decision"]


def test_payload_defensively_copied_on_append(tmp_path):
    ledger = EventLedger(path=str(tmp_path / "events.json"))
    payload = {"nested": {"value": 1}}
    ledger.append(DecisionEvent(stage="parsing", input_id="raw", output_id="parsed", payload=payload))

    payload["nested"]["value"] = 2

    assert ledger.all_events()[0]["payload"]["nested"]["value"] == 1


def test_duplicate_event_id_rejected(tmp_path):
    ledger = EventLedger(path=str(tmp_path / "events.json"))
    event = DecisionEvent(stage="parsing", input_id="raw", output_id="parsed", event_id="event-1")
    ledger.append(event)

    with pytest.raises(ValueError, match="Duplicate event_id"):
        ledger.append(event)


def test_malformed_event_fails_on_read(tmp_path):
    path = tmp_path / "events.json"
    path.write_text(json.dumps({"events": [{"stage": "parsing"}]}), encoding="utf-8")
    ledger = EventLedger(path=str(path))

    with pytest.raises(ValueError, match="Malformed event"):
        ledger.all_events()


def test_missing_replay_stage_fails(tmp_path):
    ledger = EventLedger(path=str(tmp_path / "events.json"))
    ledger.append(DecisionEvent(stage="parsing", input_id="raw", output_id="parsed", trace_id="trace-1"))

    with pytest.raises(ValueError, match="Missing required stage"):
        ledger.replay_trace("trace-1", required_stages=["parsing", "execution"])
