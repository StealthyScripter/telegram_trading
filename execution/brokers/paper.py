from datetime import datetime, timezone

from execution.brokers.base import BaseBroker


class PaperBroker(BaseBroker):
    def __init__(self, account_id: str = "paper-account", price: float = 1.1000):
        self.env = "paper"
        self.account_id = account_id
        self.price = price
        self._trades: dict[str, dict] = {}
        self._next_id = 1

    def get_price(self, symbol: str):
        return {
            "bid": self.price - 0.0001,
            "ask": self.price + 0.0001,
            "mid": self.price,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tradeable": True,
        }

    def place_order(self, symbol, units, entry_price=None, take_profit=None, stop_loss=None):
        order_id = str(self._next_id)
        self._next_id += 1
        trade_id = str(self._next_id)
        self._next_id += 1
        fill_price = str(entry_price or self.price)

        trade = {
            "id": trade_id,
            "instrument": symbol,
            "currentUnits": str(units),
            "price": fill_price,
            "state": "OPEN",
            "takeProfit": take_profit,
            "stopLoss": stop_loss,
            "openTime": datetime.now(timezone.utc).isoformat(),
        }
        self._trades[trade_id] = trade

        return {
            "orderCreateTransaction": {
                "id": order_id,
                "type": "MARKET_ORDER" if entry_price is None else "LIMIT_ORDER",
                "instrument": symbol,
                "units": str(units),
                "reason": "CLIENT_ORDER",
            },
            "orderFillTransaction": {
                "id": trade_id,
                "orderID": order_id,
                "instrument": symbol,
                "units": str(units),
                "price": fill_price,
                "reason": "MARKET_ORDER",
                "tradeOpened": {
                    "tradeID": trade_id,
                    "price": fill_price,
                    "units": str(units),
                },
            },
        }

    def get_open_trades(self, symbol: str | None = None):
        trades = [
            trade for trade in self._trades.values()
            if trade.get("state") == "OPEN"
        ]

        if symbol:
            trades = [trade for trade in trades if trade.get("instrument") == symbol]

        return trades

    def get_trade(self, trade_id: str):
        return self._trades.get(str(trade_id))

    def close_trade(self, trade_id: str):
        trade = self._trades.get(str(trade_id))
        if not trade:
            return {"orderFillTransaction": {"tradesClosed": []}}

        trade["state"] = "CLOSED"
        trade["closeTime"] = datetime.now(timezone.utc).isoformat()

        return {
            "orderFillTransaction": {
                "reason": "MARKET_ORDER_TRADE_CLOSE",
                "tradesClosed": [
                    {
                        "tradeID": str(trade_id),
                        "price": str(self.price),
                        "realizedPL": "0",
                    }
                ],
            }
        }

    def close_open_trades(self, symbol: str | None = None):
        return [
            self.close_trade(trade["id"])
            for trade in list(self.get_open_trades(symbol=symbol))
        ]
