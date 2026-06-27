from backtesting.channel_scorecard import ChannelScorecard
from backtesting.signal_backtester import SignalBacktester


class BacktestRunner:
    def __init__(self):
        self.backtester = SignalBacktester()
        self.scorecard = ChannelScorecard()

    def run(self, signals: list[dict], candles_by_symbol: dict[str, list[dict]]):
        results = []

        for signal in signals:
            if signal.get("parse_status") != "VALID_SIGNAL":
                continue

            parsed = signal["parsed_signal"]
            symbol = parsed["symbol"]

            candles = candles_by_symbol.get(symbol)

            if not candles:
                results.append(
                    {
                        "signal_id": signal["signal_id"],
                        "source": signal["source"],
                        "symbol": symbol,
                        "status": "NO_MARKET_DATA",
                        "realized_r": None,
                    }
                )
                continue

            result = self.backtester.backtest_signal(signal, candles)
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
            "results": results,
            "score": score,
        }
