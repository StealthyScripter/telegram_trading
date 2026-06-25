from signals.signal_parser import SignalParser, SignalParseStatus


class SignalProcessor:
    def __init__(self):
        self.parser = SignalParser()

    def process_raw_signal(self, raw_signal: dict) -> dict:
        parsed = self.parser.parse(raw_signal["raw_text"])

        raw_signal["parse_status"] = parsed.status.value
        raw_signal["parsed_signal"] = parsed.to_dict()

        if parsed.status == SignalParseStatus.VALID_SIGNAL:
            raw_signal["execution_status"] = "READY_FOR_PAPER"
        else:
            raw_signal["execution_status"] = "OBSERVE_ONLY"

        return raw_signal

