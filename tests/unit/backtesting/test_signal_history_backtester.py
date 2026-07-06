from datetime import datetime

from backtesting.signal_history_backtester import SignalHistoryBacktester


def test_signal_history_backtester_runs_source_report():
    class FakeSignalStore:
        def all_signals(self):
            return [
                {
                    "signal_id": "telegram:1",
                    "source": "test_channel",
                    "posted_at": "2026-01-01T10:00:00+00:00",
                    "parse_status": "VALID_SIGNAL",
                    "parsed_signal": {
                        "symbol": "EUR_USD",
                        "action": "buy",
                        "entry_price": "1.1000",
                        "stop_loss": "1.0950",
                        "take_profits": ["1.1100"],
                    },
                }
            ]

    class FakeCandleLoader:
        def fetch_candles_for_signal_window(self, symbol, posted_at, hours_after, granularity):
            return [
                {
                    "time": datetime.fromisoformat("2026-01-01T10:00:00+00:00"),
                    "open": 1.1000,
                    "high": 1.1110,
                    "low": 1.0990,
                    "close": 1.1100,
                }
            ]

    runner = SignalHistoryBacktester(
        signal_store=FakeSignalStore(),
        candle_loader=FakeCandleLoader(),
    )

    report = runner.run_for_source("test_channel")

    assert report["source"] == "test_channel"
    assert report["signals_tested"] == 1
    assert report["results"][0]["status"] == "WIN"
    assert report["score"]["wins"] == 1
