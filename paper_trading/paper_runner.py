from paper_trading.paper_store import PaperTradeStore


class PaperRunner:
    def __init__(self):
        self.store = PaperTradeStore()

    def paper_trade_signal(self, signal: dict):
        if signal.get("execution_status") != "READY_FOR_PAPER":
            return {
                "created": False,
                "reason": "signal_not_ready_for_paper",
            }

        parsed = signal.get("parsed_signal") or {}

        required = ["symbol", "action", "stop_loss", "take_profits"]

        missing = [field for field in required if not parsed.get(field)]

        if missing:
            return {
                "created": False,
                "reason": f"missing_fields: {missing}",
            }

        trade = self.store.create_paper_trade(signal)

        return {
            "created": True,
            "paper_trade": trade,
        }
    