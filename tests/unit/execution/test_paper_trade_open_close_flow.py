from contracts.execution_result import ContractExecutionStatus, ExecutionResult
from execution.brokers.paper import PaperBroker


def test_paper_trade_open_close_flow_replaces_safe_oanda_behavior(monkeypatch):
    touched = {"oanda": False}

    def fail_if_oanda_touched(*args, **kwargs):
        touched["oanda"] = True
        raise AssertionError("OANDA must not be touched by safe paper flow")

    monkeypatch.setattr("execution.brokers.oanda.OandaBroker.__init__", fail_if_oanda_touched)
    monkeypatch.setattr("execution.brokers.factory.OandaBroker", fail_if_oanda_touched)

    broker = PaperBroker(account_id="paper-safe", price=1.1000)
    open_response = broker.place_order(
        symbol="EUR_USD",
        units=1000,
        take_profit="1.1100",
        stop_loss="1.0950",
    )
    fill = open_response["orderFillTransaction"]
    trade_id = fill["tradeOpened"]["tradeID"]

    execution_result = ExecutionResult(
        execution_request_id="paper-request-1",
        status=ContractExecutionStatus.FILLED,
        broker="paper",
        account_id=broker.account_id,
        symbol="EUR_USD",
        action="buy",
        requested_units=1000,
        broker_trade_id=trade_id,
        broker_order_id=fill["orderID"],
        fill_price=fill["tradeOpened"]["price"],
        reason=fill["reason"],
        raw_response=open_response,
    )

    assert execution_result.status == ContractExecutionStatus.FILLED
    assert execution_result.broker_trade_id is not None
    assert broker.get_trade(trade_id)["state"] == "OPEN"

    close_response = broker.close_trade(trade_id)

    assert "orderFillTransaction" in close_response
    assert broker.get_trade(trade_id)["state"] == "CLOSED"
    assert broker.get_open_trades() == []
    assert touched["oanda"] is False
