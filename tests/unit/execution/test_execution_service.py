from contracts.execution_request import ExecutionRequest
from contracts.execution_result import ContractExecutionStatus, ExecutionResult
from execution.execution_service import ExecutionService


class FakeExecutor:
    def execute_request(self, request):
        return ExecutionResult(
            execution_request_id=request.id,
            status=ContractExecutionStatus.FILLED,
            broker=request.broker,
            account_id=request.account_id or "acct-1",
            symbol=request.symbol,
            action=request.action,
            requested_units=request.units,
            broker_trade_id="trade-1",
        )


def test_execution_service_accepts_execution_request():
    request = ExecutionRequest(
        capital_allocation_id="capital-1",
        source="pytest",
        broker="oanda",
        account_id="acct-1",
        symbol="EUR_USD",
        action="buy",
        units=1000,
    )

    result = ExecutionService(executor=FakeExecutor()).execute(request)

    assert result.execution_request_id == request.id
    assert result.status == ContractExecutionStatus.FILLED
    assert result.broker_trade_id == "trade-1"
