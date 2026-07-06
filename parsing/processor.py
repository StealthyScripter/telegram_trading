from events.event_store import EventStore
from events.trade_event import TradeEvent, TradeEventType
from parsing.parser import SignalParser, SignalParseStatus


class SignalProcessor:
    def __init__(self):
        self.parser = SignalParser()
        self.event_store = EventStore()

    def process_raw_signal(self, raw_signal: dict) -> dict:
        parsed = self.parser.parse(raw_signal["raw_text"])

        raw_signal["parse_status"] = parsed.status.value
        raw_signal["parsed_signal"] = parsed.to_dict()

        if parsed.status == SignalParseStatus.VALID_SIGNAL:
            raw_signal["execution_status"] = "READY_FOR_PAPER"
        else:
            raw_signal["execution_status"] = "OBSERVE_ONLY"

        self.event_store.append(
            TradeEvent(
                event_type=TradeEventType.SIGNAL_PARSED,
                source=raw_signal.get("source"),
                signal_id=raw_signal.get("signal_id"),
                symbol=raw_signal["parsed_signal"].get("symbol"),
                payload={
                    "parse_status": raw_signal["parse_status"],
                    "parsed_signal": raw_signal["parsed_signal"],
                    "execution_status": raw_signal["execution_status"],
                },
            )
        )

        return raw_signal
