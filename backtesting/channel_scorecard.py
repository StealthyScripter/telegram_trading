class ChannelScorecard:
    def score(self, trades: list[dict]) -> dict:
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "net_r": 0,
                "profit_factor": 0,
            }

        closed = [trade for trade in trades if trade.get("status") == "CLOSED"]

        wins = [trade for trade in closed if (trade.get("realized_r") or 0) > 0]
        losses = [trade for trade in closed if (trade.get("realized_r") or 0) < 0]

        gross_win = sum(trade["realized_r"] for trade in wins)
        gross_loss = abs(sum(trade["realized_r"] for trade in losses))

        return {
            "total_trades": len(trades),
            "closed_trades": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(closed) if closed else 0,
            "net_r": sum((trade.get("realized_r") or 0) for trade in closed),
            "profit_factor": gross_win / gross_loss if gross_loss else None,
        }
