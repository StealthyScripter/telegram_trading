from datetime import datetime, timezone

from config.instruments import get_instrument_meta


class TradeValidator:
    def validate_basic(self, trade):
        if not trade.symbol:
            raise ValueError("Symbol is required")

        if trade.action not in ["buy", "sell"]:
            raise ValueError("Action must be buy or sell")

        meta = get_instrument_meta(trade.symbol)

        if trade.units < meta.min_units:
            raise ValueError(
                f"Units below minimum for {trade.symbol}: {meta.min_units}"
            )

    def validate_tp_sl_direction(self, trade, current_price: float):
        tp = float(trade.take_profit) if trade.take_profit else None
        sl = float(trade.stop_loss) if trade.stop_loss else None

        if trade.action == "buy":
            if tp and tp <= current_price:
                raise ValueError("Buy take profit must be above current price")
            if sl and sl >= current_price:
                raise ValueError("Buy stop loss must be below current price")

        if trade.action == "sell":
            if tp and tp >= current_price:
                raise ValueError("Sell take profit must be below current price")
            if sl and sl <= current_price:
                raise ValueError("Sell stop loss must be above current price")

    def validate_quote_freshness(self, quote: dict, symbol: str):
        meta = get_instrument_meta(symbol)
        timestamp = quote.get("timestamp")

        if not timestamp:
            raise ValueError("Quote missing timestamp")

        quote_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - quote_time

        if age.total_seconds() > meta.max_quote_age_seconds:
            raise ValueError(
                f"Quote is stale: {age.total_seconds()} seconds old "
                f"(max allowed: {meta.max_quote_age_seconds})"
            )

    def validate_spread(self, quote: dict, symbol: str):
        meta = get_instrument_meta(symbol)
        spread = quote["ask"] - quote["bid"]

        if spread > meta.max_spread:
            raise ValueError(f"Spread too wide: {spread}")

    def normalize_price(self, symbol: str, price: float) -> str:
        meta = get_instrument_meta(symbol)
        return f"{price:.{meta.price_precision}f}"
