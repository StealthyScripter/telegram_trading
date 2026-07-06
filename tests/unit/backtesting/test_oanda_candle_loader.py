from backtesting.oanda_candle_loader import OandaCandleLoader


class FakeBroker:
    def get_candles(self, symbol, granularity, from_time, to_time):
        return [
            {
                "complete": True,
                "time": "2026-01-01T10:00:00.000000000Z",
                "volume": 100,
                "mid": {
                    "o": "1.1000",
                    "h": "1.1100",
                    "l": "1.0900",
                    "c": "1.1050",
                },
            }
        ]


def test_oanda_candle_loader_normalizes_candles():
    loader = OandaCandleLoader(broker=FakeBroker())

    candles = loader.fetch_candles_for_signal_window(
        symbol="EUR_USD",
        posted_at="2026-01-01T10:00:00+00:00",
    )

    assert len(candles) == 1
    assert candles[0]["open"] == 1.1000
    assert candles[0]["high"] == 1.1100
    assert candles[0]["low"] == 1.0900
    assert candles[0]["close"] == 1.1050
