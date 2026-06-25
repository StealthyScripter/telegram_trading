from execution.models import ExecutionStatus


class BrokerReconciler:
    def verify_execution(self, broker, result):
        if result.status != ExecutionStatus.FILLED:
            return result

        if not result.broker_trade_id:
            result.status = ExecutionStatus.DISCREPANCY
            result.reason = "Filled response missing broker_trade_id"
            return result

        broker_trade = broker.get_trade(result.broker_trade_id)

        if not broker_trade:
            result.status = ExecutionStatus.DISCREPANCY
            result.reason = "Trade filled locally but missing from broker state"
            return result

        if broker_trade.get("instrument") != result.symbol:
            result.status = ExecutionStatus.DISCREPANCY
            result.reason = "Broker trade symbol mismatch"
            return result

        return result
