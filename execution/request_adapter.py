from contracts.execution_request import ExecutionRequest
from controls.trade_controls import OpenTradePolicy
from execution.models import TradeRequest


class ExecutionRequestAdapter:
    def to_trade_request(
        self,
        request: ExecutionRequest,
        open_trade_policy: OpenTradePolicy = OpenTradePolicy.REJECT_IF_EXISTS,
    ) -> TradeRequest:
        return TradeRequest(
            symbol=request.symbol,
            action=request.action,
            units=request.units,
            source=request.source,
            broker=request.broker,
            strategy_account=request.strategy_account,
            broker_account_id=request.account_id,
            entry_price=request.entry_price,
            take_profit=request.take_profit,
            stop_loss=request.stop_loss,
            external_signal_id=request.external_signal_id or request.id,
            open_trade_policy=open_trade_policy,
        )
