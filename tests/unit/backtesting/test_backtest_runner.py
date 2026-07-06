from datetime import datetime, timezone

from backtesting.backtest_runner import BacktestRunner


def test_backtest_runner_scores_signals():
    runner = BacktestRunner()

    signal = {
        "signal_id": "telegram:1",
        "source": "telegram_test",
        "posted_at": datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc).isoformat(),
        "parse_status": "VALID_SIGNAL",
        "parsed_signal": {
            "symbol": "EUR_USD",
            "action": "buy",
            "entry_price": "1.1000",
            "stop_loss": "1.0950",
            "take_profits": ["1.1100"],
        },
    }

    candles = [
        {
            "time": datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            "open": 1.1000,
            "high": 1.1110,
            "low": 1.0990,
            "close": 1.1100,
        }
    ]

    report = runner.run(
        signals=[signal],
        candles_by_symbol={"EUR_USD": candles},
    )

    assert len(report["results"]) == 1
    assert report["results"][0]["status"] == "WIN"
    assert report["score"]["wins"] == 1
