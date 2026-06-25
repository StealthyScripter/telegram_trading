from enum import Enum


class OpenTradePolicy(str, Enum):
    REJECT_IF_EXISTS = "reject_if_exists"
    CLOSE_EXISTING_FIRST = "close_existing_first"
    ALLOW_ADD = "allow_add"


class TradeControls:
    def enforce_open_trade_policy(
        self,
        broker,
        symbol: str,
        policy: OpenTradePolicy,
    ):
        open_trades = broker.get_open_trades(symbol=symbol)

        if not open_trades:
            return

        if policy == OpenTradePolicy.REJECT_IF_EXISTS:
            raise RuntimeError(
                f"Open trade already exists for {symbol}. New trade rejected."
            )

        if policy == OpenTradePolicy.CLOSE_EXISTING_FIRST:
            broker.close_open_trades(symbol=symbol)
            return

        if policy == OpenTradePolicy.ALLOW_ADD:
            return

        raise ValueError(f"Unsupported open trade policy: {policy}")
