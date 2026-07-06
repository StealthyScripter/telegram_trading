from datetime import datetime, timezone

from config.instruments import get_instrument_meta
from execution.brokers.base import BaseBroker, BrokerCapabilities, BrokerMetadata, NormalizedBrokerError


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

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            supports_market_orders=True,
            supports_limit_orders=True,
            supports_trade_close=True,
            supports_partial_fill=False,
            supports_idempotency=True,
        )

    def metadata(self, symbol: str | None = None) -> BrokerMetadata:
        min_units = 1
        price_precision = None
        if symbol:
            meta = get_instrument_meta(symbol)
            min_units = meta.min_units
            price_precision = meta.price_precision

        return BrokerMetadata(
            broker="paper",
            account_id=self.account_id,
            env=self.env,
            symbol=symbol,
            min_units=min_units,
            price_precision=price_precision,
        )

    def normalize_error(self, error: Exception) -> NormalizedBrokerError:
        if isinstance(error, TimeoutError):
            return NormalizedBrokerError(
                code="BROKER_TIMEOUT",
                message="Paper broker timeout",
                retryable=True,
                raw_error_type=error.__class__.__name__,
            )

        return NormalizedBrokerError(
            code="BROKER_REJECTED",
            message=str(error),
            retryable=False,
            raw_error_type=error.__class__.__name__,
        )
