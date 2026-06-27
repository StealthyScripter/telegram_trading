from datetime import datetime


class SignalBacktester:
    def backtest_signal(
        self,
        signal: dict,
        candles: list[dict],
        max_candles: int | None = None,
    ) -> dict:
        parsed = signal["parsed_signal"]

        symbol = parsed["symbol"]
        action = parsed["action"]
        entry_price = parsed.get("entry_price")
        stop_loss = float(parsed["stop_loss"])
        take_profit = float(parsed["take_profits"][0])

        posted_at = self._parse_time(signal["posted_at"])

        test_candles = [
            candle for candle in candles
            if candle["time"] >= posted_at
        ]

        if max_candles:
            test_candles = test_candles[:max_candles]

        if not test_candles:
            return self._result(
                signal=signal,
                status="NO_MARKET_DATA",
                symbol=symbol,
                action=action,
            )

        if entry_price:
            entry = float(entry_price)
            entered = False
        else:
            entry = test_candles[0]["open"]
            entered = True

        risk = abs(entry - stop_loss)

        if risk == 0:
            return self._result(
                signal=signal,
                status="INVALID_RISK",
                symbol=symbol,
                action=action,
                entry_price=entry,
            )

        for candle in test_candles:
            if not entered:
                if self._entry_hit(action, entry, candle):
                    entered = True
                else:
                    continue

            outcome = self._check_outcome(
                action=action,
                candle=candle,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

            if outcome == "TP_HIT":
                return self._result(
                    signal=signal,
                    status="WIN",
                    symbol=symbol,
                    action=action,
                    entry_price=entry,
                    exit_price=take_profit,
                    realized_r=abs(take_profit - entry) / risk,
                    exit_time=candle["time"].isoformat(),
                )

            if outcome == "SL_HIT":
                return self._result(
                    signal=signal,
                    status="LOSS",
                    symbol=symbol,
                    action=action,
                    entry_price=entry,
                    exit_price=stop_loss,
                    realized_r=-1,
                    exit_time=candle["time"].isoformat(),
                )

        if not entered:
            return self._result(
                signal=signal,
                status="NOT_TRIGGERED",
                symbol=symbol,
                action=action,
                entry_price=entry,
            )

        last_close = test_candles[-1]["close"]
        unrealized_r = self._unrealized_r(
            action=action,
            entry=entry,
            last_price=last_close,
            risk=risk,
        )

        return self._result(
            signal=signal,
            status="OPEN",
            symbol=symbol,
            action=action,
            entry_price=entry,
            exit_price=last_close,
            realized_r=unrealized_r,
            exit_time=test_candles[-1]["time"].isoformat(),
        )

    def _entry_hit(self, action: str, entry: float, candle: dict) -> bool:
        return candle["low"] <= entry <= candle["high"]

    def _check_outcome(
        self,
        action: str,
        candle: dict,
        stop_loss: float,
        take_profit: float,
    ) -> str | None:
        if action == "buy":
            sl_hit = candle["low"] <= stop_loss
            tp_hit = candle["high"] >= take_profit
        else:
            sl_hit = candle["high"] >= stop_loss
            tp_hit = candle["low"] <= take_profit

        if sl_hit and tp_hit:
            return "SL_HIT"

        if tp_hit:
            return "TP_HIT"

        if sl_hit:
            return "SL_HIT"

        return None

    def _unrealized_r(
        self,
        action: str,
        entry: float,
        last_price: float,
        risk: float,
    ) -> float:
        if action == "buy":
            return (last_price - entry) / risk

        return (entry - last_price) / risk

    def _parse_time(self, value):
        if isinstance(value, datetime):
            return value

        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _result(
        self,
        signal: dict,
        status: str,
        symbol: str,
        action: str,
        entry_price=None,
        exit_price=None,
        realized_r=None,
        exit_time=None,
    ):
        return {
            "signal_id": signal["signal_id"],
            "source": signal["source"],
            "symbol": symbol,
            "action": action,
            "status": status,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "realized_r": realized_r,
            "posted_at": signal["posted_at"],
            "exit_time": exit_time,
        }
