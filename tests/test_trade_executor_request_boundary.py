from contracts.execution_request import ExecutionRequest
from contracts.execution_result import ContractExecutionStatus
from execution.models import ExecutionResult, ExecutionStatus
from execution.trade_executor import TradeExecutor


def test_trade_executor_execute_request_returns_contract_result(monkeypatch):
    executor = TradeExecutor(broker_name="oanda")

    def fake_execute_trade(trade):
        return ExecutionResult(
            status=ExecutionStatus.FILLED,
            broker="oanda",
            account_id="acct-1",
            symbol=trade.symbol,
            action=trade.action,
            requested_units=trade.units,
            broker_trade_id="trade-1",
            broker_order_id="order-1",
            reason="MARKET_ORDER",
            raw_response={"ok": True},
        )

    monkeypatch.setattr(executor, "execute_trade", fake_execute_trade)

    request = ExecutionRequest(
        capital_allocation_id="capital-1",
        source="pytest",
        broker="oanda",
        account_id="acct-1",
        symbol="EUR_USD",
        action="buy",
        units=1000,
        take_profit="1.1400",
        stop_loss="1.1300",
    )

    result = executor.execute_request(request)

    assert result.execution_request_id == request.id
    assert result.status == ContractExecutionStatus.FILLED
    assert result.broker == "oanda"
    assert result.account_id == "acct-1"
    assert result.symbol == "EUR_USD"
    assert result.broker_trade_id == "trade-1"


def test_trade_executor_maps_canceled_status(monkeypatch):
    executor = TradeExecutor(broker_name="oanda")

    def fake_execute_trade(trade):
        return ExecutionResult(
            status=ExecutionStatus.CANCELED,
            broker="oanda",
            account_id="acct-1",
            symbol=trade.symbol,
            action=trade.action,
            requested_units=trade.units,
            broker_order_id="order-1",
            reason="FIFO_VIOLATION",
            raw_response={},
        )

    monkeypatch.setattr(executor, "execute_trade", fake_execute_trade)

    request = ExecutionRequest(
        capital_allocation_id="capital-1",
        source="pytest",
        broker="oanda",
        account_id="acct-1",
        symbol="EUR_USD",
        action="buy",
        units=1000,
    )

    result = executor.execute_request(request)

    assert result.status == ContractExecutionStatus.CANCELED
    assert result.reason == "FIFO_VIOLATION"
