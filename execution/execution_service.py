from contracts.execution_request import ExecutionRequest
from contracts.execution_result import ExecutionResult
from execution.trade_executor import TradeExecutor


class ExecutionService:
    def __init__(self, executor: TradeExecutor | None = None):
        self.executor = executor or TradeExecutor()

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if not isinstance(request, ExecutionRequest):
            raise TypeError("ExecutionService.execute requires ExecutionRequest")

        return self.executor.execute_request(request)
