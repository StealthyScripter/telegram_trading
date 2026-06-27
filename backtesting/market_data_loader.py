import csv
from datetime import datetime, timezone
from pathlib import Path


class MarketDataLoader:
    def load_csv(self, path: str) -> list[dict]:
        candles = []

        with Path(path).open("r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                candles.append(
                    {
                        "time": self._parse_time(row["time"]),
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                    }
                )

        return candles

    def _parse_time(self, value: str):
        value = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(value)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed

    def candles_after(self, candles: list[dict], start_time):
        return [
            candle for candle in candles
            if candle["time"] >= start_time
        ]
