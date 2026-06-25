import os
from dotenv import load_dotenv

from brokers.oanda import OandaBroker
from config.instruments import get_instrument_meta
from controls.trade_controls import OpenTradePolicy
from execution.close_executor import CloseExecutor
from execution.models import ExecutionStatus, TradeRequest
from execution.trade_executor import TradeExecutor
from reconciliation.startup_reconciler import StartupReconciler
from routing.router import DynamicOrderRouter

load_dotenv()

CLOSE_AFTER_TEST = True


def main():
    symbol = "EUR_USD"
    action = "buy"
    units = 1000
    source = "manual_main"
    broker_name = os.getenv("DEFAULT_BROKER", "oanda")

    router = DynamicOrderRouter()
    route = router.resolve_route(
        source=source,
        broker=broker_name,
    )

    account_id = route["account_id"]
    strategy_account = route["strategy_account"]

    reconciler = StartupReconciler()
    startup_report = reconciler.run_for_account(
        account_id=account_id,
        symbol=symbol,
    )

    if startup_report["unfinished_attempts"]:
        print("RED FLAG: There are unfinished local execution attempts.")
        print("Check execution.log and data/execution_state.json")

    if startup_report["unknown_open_trades"]:
        print("RED FLAG: Broker has open trades not known by local state.")
        print("Check OANDA and data/execution_state.json")

    price_broker = OandaBroker(account_id=account_id)
    price = price_broker.get_price(symbol)

    meta = get_instrument_meta(symbol)
    current_price = price["ask"] if action == "buy" else price["bid"]

    tp_pips = 5
    sl_pips = 5

    if action == "buy":
        take_profit = current_price + (tp_pips * meta.pip_size)
        stop_loss = current_price - (sl_pips * meta.pip_size)
    else:
        take_profit = current_price - (tp_pips * meta.pip_size)
        stop_loss = current_price + (sl_pips * meta.pip_size)

    take_profit = f"{take_profit:.{meta.price_precision}f}"
    stop_loss = f"{stop_loss:.{meta.price_precision}f}"

    trade = TradeRequest(
        symbol=symbol,
        action=action,
        units=units,
        source=source,
        broker=broker_name,
        strategy_account=strategy_account,
        broker_account_id=None,
        entry_price=None,
        take_profit=take_profit,
        stop_loss=stop_loss,
        external_signal_id=f"{source}-{symbol}-{action}",
        open_trade_policy=OpenTradePolicy.CLOSE_EXISTING_FIRST,
    )

    print("=" * 60)
    print(f"Broker Environment : {os.getenv('OANDA_ENV')}")
    print(f"Broker             : {trade.broker}")
    print(f"Source             : {trade.source}")
    print(f"Route Reason       : {route['route_reason']}")
    print(f"Strategy Account   : {trade.strategy_account}")
    print(f"Account ID         : {account_id}")
    print(f"Symbol             : {trade.symbol}")
    print(f"Action             : {trade.action}")
    print(f"Units              : {trade.units}")
    print(f"Current Price      : {current_price}")
    print(f"Take Profit        : {trade.take_profit}")
    print(f"Stop Loss          : {trade.stop_loss}")
    print(f"Open Trade Policy  : {trade.open_trade_policy}")
    print(f"Close After Test   : {CLOSE_AFTER_TEST}")
    print("=" * 60)

    executor = TradeExecutor(broker_name=broker_name)
    response = executor.execute_trade(trade)

    print("Trade response:")
    print(response)

    if response.status == ExecutionStatus.FILLED:
        print("\nTrade successfully opened")

        if CLOSE_AFTER_TEST:
            print("TEST MODE ENABLED - Closing trade immediately")

            close_executor = CloseExecutor()
            close_response = close_executor.close_trade(
                broker_name=response.broker,
                account_id=response.account_id,
                trade_id=response.broker_trade_id,
                symbol=response.symbol,
                reason="close_after_test",
            )

            print("Close response:")
            print(close_response)

        else:
            print(
                f"WARNING: Trade {response.broker_trade_id} "
                f"remains OPEN in account {response.account_id}"
            )

    elif response.status == ExecutionStatus.CANCELED:
        print(f"Trade canceled: {response.reason}")

    else:
        print(f"Unexpected execution status: {response.status}")


if __name__ == "__main__":
    main()
