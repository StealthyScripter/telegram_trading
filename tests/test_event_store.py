from events.event_store import EventStore
from events.trade_event import TradeEvent, TradeEventType


def test_event_store_appends_event(tmp_path):
    store = EventStore(path=str(tmp_path / "events.json"))

    event = TradeEvent(
        event_type=TradeEventType.SIGNAL_RECEIVED,
        source="telegram_test",
        signal_id="telegram:1",
        payload={"raw_text": "BUY EURUSD"},
    )

    saved = store.append(event)

    assert saved["event_type"] == "SIGNAL_RECEIVED"
    assert saved["source"] == "telegram_test"
    assert len(store.all_events()) == 1


def test_event_store_finds_by_signal_id(tmp_path):
    store = EventStore(path=str(tmp_path / "events.json"))

    store.append(
        TradeEvent(
            event_type=TradeEventType.SIGNAL_RECEIVED,
            signal_id="signal-1",
        )
    )

    store.append(
        TradeEvent(
            event_type=TradeEventType.SIGNAL_PARSED,
            signal_id="signal-1",
        )
    )

    events = store.find_by_signal_id("signal-1")

    assert len(events) == 2


def test_event_store_finds_by_trade_id(tmp_path):
    store = EventStore(path=str(tmp_path / "events.json"))

    store.append(
        TradeEvent(
            event_type=TradeEventType.ORDER_FILLED,
            trade_id="trade-1",
        )
    )

    events = store.find_by_trade_id("trade-1")

    assert len(events) == 1
    assert events[0]["event_type"] == "ORDER_FILLED"
