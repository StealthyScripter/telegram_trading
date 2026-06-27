import json
import sys

from backtesting.signal_history_backtester import SignalHistoryBacktester


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python backtest_signal_source.py <source>")

    source = sys.argv[1]

    runner = SignalHistoryBacktester()

    report = runner.run_for_source(
        source=source,
        hours_after=24,
        granularity="M5",
    )

    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
