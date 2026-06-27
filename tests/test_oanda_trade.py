import pytest
from dotenv import load_dotenv

from brokers.oanda import OandaBroker
from execution.trade_executor import TradeExecutor
from execution.models import TradeRequest
from execution.models import ExecutionStatus

load_dotenv()


def calculate_valid_tp_sl(
    action: str,
    current_price: float,
    tp_pips: int = 50,
    sl_pips: int = 50,
    pip_size: float = 0.0001,
):
    if action == "buy":
        take_profit = current_price + (tp_pips * pip_size)
        stop_loss = current_price - (sl_pips * pip_size)
    elif action == "sell":
        take_profit = current_price - (tp_pips * pip_size)
        stop_loss = current_price + (sl_pips * pip_size)
    else:
        raise ValueError("action must be 'buy' or 'sell'")

    return round(take_profit, 5), round(stop_loss, 5)

@pytest.mark.integration
def test_oanda_market_trade_and_close():
    broker = OandaBroker()
    executor = TradeExecutor(broker_name="oanda")

    symbol = "EUR_USD"
    action = "buy"
    units = 1000

    existing_trades = broker.get_open_trades(symbol=symbol)

    if existing_trades:
        print(f"Closing {len(existing_trades)} existing {symbol} trade(s)")
        broker.close_open_trades(symbol=symbol)

    price = broker.get_price(symbol)
    current_price = price["ask"] if action == "buy" else price["bid"]

    take_profit, stop_loss = calculate_valid_tp_sl(
        action=action,
        current_price=current_price,
        tp_pips=50,
        sl_pips=50,
    )

    print(f"Current price: {current_price}")
    print(f"Take profit: {take_profit}")
    print(f"Stop loss: {stop_loss}")

    trade = TradeRequest(
        symbol=symbol,
        action=action,
        units=units,
        source="pytest",
        strategy_account="scalping",
        entry_price=None,
        take_profit=str(take_profit),
        stop_loss=str(stop_loss),
        external_signal_id="test-oanda-market-trade",
    )

    open_response = executor.execute_trade(trade)

    print("Open trade response:")
    print(open_response)

    assert open_response.status == ExecutionStatus.FILLED
    assert open_response.broker_trade_id is not None

    trade_id = open_response.broker_trade_id

    close_response = broker.close_trade(trade_id)

    print("Close trade response:")
    print(close_response)

    assert "orderFillTransaction" in close_response
