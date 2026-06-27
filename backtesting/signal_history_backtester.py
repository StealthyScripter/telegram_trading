from backtesting.oanda_candle_loader import OandaCandleLoader
from backtesting.signal_backtester import SignalBacktester
from backtesting.channel_scorecard import ChannelScorecard
from signals.signal_store import SignalStore


class SignalHistoryBacktester:
    def __init__(
        self,
        signal_store=None,
        candle_loader=None,
        backtester=None,
        scorecard=None,
    ):
        self.signal_store = signal_store or SignalStore()
        self.candle_loader = candle_loader or OandaCandleLoader()
        self.backtester = backtester or SignalBacktester()
        self.scorecard = scorecard or ChannelScorecard()

    def run_for_source(
        self,
        source: str,
        hours_after: int = 24,
        granularity: str = "M5",
    ):
        signals = [
            signal for signal in self.signal_store.all_signals()
            if signal.get("source") == source
            and signal.get("parse_status") == "VALID_SIGNAL"
        ]

        results = []

        for signal in signals:
            parsed = signal["parsed_signal"]
            symbol = parsed["symbol"]

            candles = self.candle_loader.fetch_candles_for_signal_window(
                symbol=symbol,
                posted_at=signal["posted_at"],
                hours_after=hours_after,
                granularity=granularity,
            )

            result = self.backtester.backtest_signal(
                signal=signal,
                candles=candles,
            )

            results.append(result)

        score = self.scorecard.score(
            [
                {
                    "status": "CLOSED" if item["status"] in ["WIN", "LOSS"] else item["status"],
                    "realized_r": item.get("realized_r"),
                }
                for item in results
            ]
        )

        return {
            "source": source,
            "signals_tested": len(results),
            "results": results,
            "score": score,
        }
