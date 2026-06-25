from brokers.oanda import OandaBroker
from data.execution_store import ExecutionStore
from monitoring.logger import ExecutionLogger


class StartupReconciler:
    def __init__(self):
        self.store = ExecutionStore()
        self.logger = ExecutionLogger()

    def run_for_account(self, account_id: str, symbol: str | None = None):
        broker = OandaBroker(account_id=account_id)

        unfinished = self.store.get_unfinished_attempts()
        open_trades = broker.get_open_trades(symbol=symbol)

        known_trade_ids = {
            str(record.get("broker_trade_id"))
            for record in self.store.all_executions()
            if record.get("broker_trade_id")
        }

        broker_open_trade_ids = {
            str(trade.get("id"))
            for trade in open_trades
        }

        unknown_open_trades = [
            trade for trade in open_trades
            if str(trade.get("id")) not in known_trade_ids
        ]

        if unfinished:
            self.logger.error(
                "red_flag_unfinished_execution_attempts",
                {
                    "account_id": account_id,
                    "symbol": symbol,
                    "unfinished_count": len(unfinished),
                    "unfinished": unfinished,
                },
            )

        if unknown_open_trades:
            self.logger.error(
                "red_flag_unknown_broker_open_trades",
                {
                    "account_id": account_id,
                    "symbol": symbol,
                    "unknown_open_trades": unknown_open_trades,
                },
            )

        return {
            "unfinished_attempts": unfinished,
            "open_trades": open_trades,
            "known_trade_ids": list(known_trade_ids),
            "broker_open_trade_ids": list(broker_open_trade_ids),
            "unknown_open_trades": unknown_open_trades,
        }
