from datetime import datetime, timedelta, timezone

from brokers.oanda import OandaBroker


class OandaCandleLoader:
    def __init__(self, broker: OandaBroker | None = None):
        self.broker = broker or OandaBroker()

    def fetch_candles_for_signal_window(
        self,
        symbol: str,
        posted_at: str,
        hours_after: int = 24,
        granularity: str = "M5",
    ):
        start = self._parse_time(posted_at)
        end = start + timedelta(hours=hours_after)

        raw_candles = self.broker.get_candles(
            symbol=symbol,
            granularity=granularity,
            from_time=start.isoformat().replace("+00:00", "Z"),
            to_time=end.isoformat().replace("+00:00", "Z"),
        )

        return [self._normalize_candle(candle) for candle in raw_candles if candle.get("complete")]

    def _normalize_candle(self, candle: dict):
        mid = candle["mid"]

        return {
            "time": self._parse_time(candle["time"]),
            "open": float(mid["o"]),
            "high": float(mid["h"]),
            "low": float(mid["l"]),
            "close": float(mid["c"]),
            "volume": candle.get("volume"),
            "complete": candle.get("complete"),
        }

    def _parse_time(self, value):
        if isinstance(value, datetime):
            dt = value
        else:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt
