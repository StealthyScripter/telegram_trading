import os
import requests


class OandaBroker:
    def __init__(self, account_id: str | None = None):
        self.env = os.getenv("OANDA_ENV", "practice")
        self.account_id = account_id or os.getenv("OANDA_ACCOUNT_ID")
        self.api_token = os.getenv("OANDA_API_TOKEN")

        if not self.account_id:
            raise ValueError("Missing OANDA account ID")

        if not self.api_token:
            raise ValueError("Missing OANDA_API_TOKEN")

        self.base_url = self._get_base_url()

        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _get_base_url(self) -> str:
        if self.env == "live":
            return "https://api-fxtrade.oanda.com"
        return "https://api-fxpractice.oanda.com"

    def get_price(self, symbol: str):
        url = f"{self.base_url}/v3/accounts/{self.account_id}/pricing"
        params = {"instruments": symbol}

        response = requests.get(url, headers=self.headers, params=params, timeout=20)
        data = response.json()

        if response.status_code >= 400:
            raise RuntimeError(f"OANDA price fetch failed: {response.status_code} - {data}")

        price = data["prices"][0]
        bid = float(price["bids"][0]["price"])
        ask = float(price["asks"][0]["price"])

        return {
            "bid": bid,
            "ask": ask,
            "mid": (bid + ask) / 2,
            "timestamp": price.get("time"),
            "tradeable": price.get("tradeable", True),
        }

    def place_order(self, symbol, units, entry_price=None, take_profit=None, stop_loss=None):
        if entry_price:
            order_type = "LIMIT"
            order = {
                "order": {
                    "type": order_type,
                    "instrument": symbol,
                    "units": str(units),
                    "price": str(entry_price),
                    "timeInForce": "GTC",
                    "positionFill": "DEFAULT",
                }
            }
        else:
            order_type = "MARKET"
            order = {
                "order": {
                    "type": order_type,
                    "instrument": symbol,
                    "units": str(units),
                    "timeInForce": "FOK",
                    "positionFill": "DEFAULT",
                }
            }

        if take_profit:
            order["order"]["takeProfitOnFill"] = {
                "price": str(take_profit),
                "timeInForce": "GTC",
            }

        if stop_loss:
            order["order"]["stopLossOnFill"] = {
                "price": str(stop_loss),
                "timeInForce": "GTC",
            }

        return self._send_order(order)

    def _send_order(self, order: dict):
        url = f"{self.base_url}/v3/accounts/{self.account_id}/orders"

        response = requests.post(url, headers=self.headers, json=order, timeout=20)

        try:
            data = response.json()
        except ValueError:
            data = {"raw_response": response.text}

        if response.status_code >= 400:
            raise RuntimeError(f"OANDA order failed: {response.status_code} - {data}")

        return data

    def get_open_trades(self, symbol: str | None = None):
        url = f"{self.base_url}/v3/accounts/{self.account_id}/openTrades"

        response = requests.get(url, headers=self.headers, timeout=20)
        data = response.json()

        if response.status_code >= 400:
            raise RuntimeError(f"OANDA open trades failed: {response.status_code} - {data}")

        trades = data.get("trades", [])

        if symbol:
            trades = [trade for trade in trades if trade.get("instrument") == symbol]

        return trades

    def get_trade(self, trade_id: str):
        url = f"{self.base_url}/v3/accounts/{self.account_id}/trades/{trade_id}"

        response = requests.get(url, headers=self.headers, timeout=20)
        data = response.json()

        if response.status_code >= 400:
            raise RuntimeError(f"OANDA trade fetch failed: {response.status_code} - {data}")

        return data.get("trade")

    def close_trade(self, trade_id: str):
        url = f"{self.base_url}/v3/accounts/{self.account_id}/trades/{trade_id}/close"

        response = requests.put(url, headers=self.headers, json={}, timeout=20)
        data = response.json()

        if response.status_code >= 400:
            raise RuntimeError(f"OANDA trade close failed: {response.status_code} - {data}")

        return data

    def close_open_trades(self, symbol: str | None = None):
        trades = self.get_open_trades(symbol=symbol)
        closed_trades = []

        for trade in trades:
            trade_id = trade["id"]
            closed_trades.append(self.close_trade(trade_id))

        return closed_trades

    def get_candles(
        self,
        symbol: str,
        granularity: str = "M5",
        count: int = 500,
        price: str = "M",
        from_time: str | None = None,
        to_time: str | None = None,
    ):
        url = f"{self.base_url}/v3/instruments/{symbol}/candles"

        params = {
            "granularity": granularity,
            "count": count,
            "price": price,
        }

        if from_time:
            params.pop("count", None)
            params["from"] = from_time

        if to_time:
            params["to"] = to_time

        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=20,
        )

        data = response.json()

        if response.status_code >= 400:
            raise RuntimeError(
                f"OANDA candles fetch failed: {response.status_code} - {data}"
            )

        return data.get("candles", [])
