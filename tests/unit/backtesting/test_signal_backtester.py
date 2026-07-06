from datetime import datetime, timezone, timedelta
import pytest
from backtesting.signal_backtester import SignalBacktester


def make_signal(action="buy"):
    return {
        "signal_id": "telegram:1",
        "source": "telegram_test",
        "posted_at": datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc).isoformat(),
        "parsed_signal": {
            "symbol": "EUR_USD",
            "action": action,
            "entry_price": "1.1000",
            "stop_loss": "1.0950" if action == "buy" else "1.1050",
            "take_profits": ["1.1100"] if action == "buy" else ["1.0900"],
        },
    }


def candle(minutes, open_, high, low, close):
    return {
        "time": datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc) + timedelta(minutes=minutes),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
    }


def test_buy_signal_hits_take_profit():
    backtester = SignalBacktester()

    candles = [
        candle(0, 1.1000, 1.1060, 1.0990, 1.1050),
        candle(1, 1.1050, 1.1110, 1.1040, 1.1100),
    ]

    result = backtester.backtest_signal(make_signal("buy"), candles)

    assert result["status"] == "WIN"
    assert result["realized_r"] == pytest.approx(2)


def test_buy_signal_hits_stop_loss():
    backtester = SignalBacktester()

    candles = [
        candle(0, 1.1000, 1.1010, 1.0940, 1.0950),
    ]

    result = backtester.backtest_signal(make_signal("buy"), candles)

    assert result["status"] == "LOSS"
    assert result["realized_r"] == -1


def test_sell_signal_hits_take_profit():
    backtester = SignalBacktester()

    candles = [
        candle(0, 1.1000, 1.1010, 1.0890, 1.0900),
    ]

    result = backtester.backtest_signal(make_signal("sell"), candles)

    assert result["status"] == "WIN"
    assert result["realized_r"] == pytest.approx(2)


def test_signal_not_triggered():
    backtester = SignalBacktester()

    candles = [
        candle(0, 1.1200, 1.1210, 1.1190, 1.1205),
    ]

    result = backtester.backtest_signal(make_signal("buy"), candles)

    assert result["status"] == "NOT_TRIGGERED"


def test_signal_open_after_window():
    backtester = SignalBacktester()

    candles = [
        candle(0, 1.1000, 1.1030, 1.0990, 1.1020),
    ]

    result = backtester.backtest_signal(make_signal("buy"), candles)

    assert result["status"] == "OPEN"
    assert round(result["realized_r"], 2) == 0.4
