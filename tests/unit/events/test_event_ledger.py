from dataclasses import FrozenInstanceError

import pytest

from events.ledger import EventLedger
from events.models import DecisionEvent


def test_decision_event_is_immutable():
    event = DecisionEvent(stage="parsing", input_id="raw-1", output_id="parsed-1")

    with pytest.raises(FrozenInstanceError):
        event.stage = "decision"


def test_event_ledger_appends_and_queries(tmp_path):
    ledger = EventLedger(path=str(tmp_path / "decision_events.json"))
    event = DecisionEvent(
        stage="parsing",
        input_id="raw-1",
        output_id="parsed-1",
        reason="ok",
        payload={"status": "VALID_SIGNAL"},
    )

    saved = ledger.append(event)

    assert saved["stage"] == "parsing"
    assert ledger.find_by_stage("parsing")[0]["output_id"] == "parsed-1"
    assert ledger.find_by_input_id("raw-1")[0]["stage"] == "parsing"
    assert ledger.find_by_output_id("parsed-1")[0]["reason"] == "ok"
    assert ledger.latest(1)[0]["event_id"] == event.event_id
