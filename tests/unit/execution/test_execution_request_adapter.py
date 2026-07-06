from contracts.execution_request import ExecutionMode, ExecutionRequest
from controls.trade_controls import OpenTradePolicy
from execution.request_adapter import ExecutionRequestAdapter


def test_execution_request_adapter_creates_trade_request():
    request = ExecutionRequest(
        capital_allocation_id="capital-1",
        source="telegram_channel",
        broker="oanda",
        account_id="acct-1",
        strategy_account="scalping",
        symbol="EUR_USD",
        action="buy",
        units=1000,
        entry_price=None,
        take_profit="1.1400",
        stop_loss="1.1300",
        mode=ExecutionMode.PAPER,
        external_signal_id="signal-1",
    )

    adapter = ExecutionRequestAdapter()

    trade = adapter.to_trade_request(
        request,
        open_trade_policy=OpenTradePolicy.CLOSE_EXISTING_FIRST,
    )

    assert trade.symbol == "EUR_USD"
    assert trade.action == "buy"
    assert trade.units == 1000
    assert trade.source == "telegram_channel"
    assert trade.broker == "oanda"
    assert trade.broker_account_id == "acct-1"
    assert trade.strategy_account == "scalping"
    assert trade.take_profit == "1.1400"
    assert trade.stop_loss == "1.1300"
    assert trade.external_signal_id == "signal-1"
    assert trade.open_trade_policy == OpenTradePolicy.CLOSE_EXISTING_FIRST


def test_execution_request_adapter_uses_request_id_when_no_signal_id():
    request = ExecutionRequest(
        capital_allocation_id="capital-1",
        source="manual",
        broker="oanda",
        symbol="EUR_USD",
        action="buy",
        units=1000,
    )

    adapter = ExecutionRequestAdapter()
    trade = adapter.to_trade_request(request)

    assert trade.external_signal_id == request.id
