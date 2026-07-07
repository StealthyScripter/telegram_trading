import uuid

from controls.bot_controls import BotControls
from controls.trade_controls import TradeControls
from data.execution_store import ExecutionStore
from events.event_store import EventStore
from events.trade_event import TradeEvent, TradeEventType
from execution.brokers.factory import BrokerFactory
from execution.idempotency import PersistentIdempotencyStore
from execution.models import ExecutionResult, ExecutionStatus
from execution.validation import TradeValidator
from monitoring.logger import ExecutionLogger
from reconciliation.broker_reconciler import BrokerReconciler
from routing.router import DynamicOrderRouter
from contracts.execution_request import ExecutionRequest
from contracts.execution_result import (
    ContractExecutionResult,
    ContractExecutionStatus,
)
from execution.request_adapter import ExecutionRequestAdapter


class TradeExecutor:
    def __init__(self, broker_name: str = "oanda"):
        self.broker_name = broker_name
        self.request_adapter = ExecutionRequestAdapter()
        self.event_store = EventStore()
        self.validator = TradeValidator()
        self.idempotency = PersistentIdempotencyStore()
        self.logger = ExecutionLogger()
        self.reconciler = BrokerReconciler()
        self.store = ExecutionStore()
        self.broker_factory = BrokerFactory()
        self.bot_controls = BotControls()
        self.trade_controls = TradeControls()
        self.dynamic_router = DynamicOrderRouter()

    def execute_trade(self, trade):
        request_id = trade.external_signal_id or str(uuid.uuid4())

        self.validator.validate_basic(trade)

        route = self.dynamic_router.resolve_route(
            source=trade.source,
            broker=trade.broker or self.broker_name,
            strategy_account=trade.strategy_account,
            explicit_account_id=trade.broker_account_id,
        )

        broker_name = route["broker"]
        account_id = route["account_id"]

        broker = self.broker_factory.create(
            broker_name=broker_name,
            account_id=account_id,
        )

        self.bot_controls.assert_can_trade(broker.env)

        key = self.idempotency.make_key(trade)

        if self.idempotency.exists(key):
            self.logger.warning(
                "duplicate_trade_blocked",
                {
                    "request_id": request_id,
                    "idempotency_key": key,
                    "broker": broker_name,
                    "account_id": account_id,
                    "symbol": trade.symbol,
                    "action": trade.action,
                    "units": trade.units,
                },
            )
            raise ValueError("Duplicate trade request blocked")

        quote = broker.get_price(trade.symbol)

        if not quote.get("tradeable", True):
            raise ValueError(f"{trade.symbol} is not tradeable")

        current_price = quote["ask"] if trade.action == "buy" else quote["bid"]

        self.validator.validate_quote_freshness(quote, trade.symbol)
        self.validator.validate_spread(quote, trade.symbol)
        self.validator.validate_tp_sl_direction(trade, current_price)

        units = trade.units if trade.action == "buy" else -trade.units

        self.trade_controls.enforce_open_trade_policy(
            broker=broker,
            symbol=trade.symbol,
            policy=trade.open_trade_policy,
        )

        attempt_payload = {
            "request_id": request_id,
            "idempotency_key": key,
            "broker": broker_name,
            "broker_env": broker.env,
            "account_id": account_id,
            "symbol": trade.symbol,
            "action": trade.action,
            "units": units,
            "take_profit": trade.take_profit,
            "stop_loss": trade.stop_loss,
            "open_trade_policy": trade.open_trade_policy.value,
            "quote": quote,
            "source": trade.source,
            "strategy": trade.strategy_account,
            "route_reason": route["route_reason"],
            "entry_price": trade.entry_price,
            "expected_entry_price": current_price,
        }

        self.store.create_attempt(request_id, attempt_payload)
        self.logger.info("trade_attempt_started", attempt_payload)

        self.event_store.append(
            TradeEvent(
                event_type=TradeEventType.ORDER_SUBMITTED,
                source=trade.source,
                signal_id=trade.external_signal_id,
                broker=broker_name,
                account_id=account_id,
                symbol=trade.symbol,
                strategy=trade.strategy_account,
                payload=attempt_payload,
            )
        )

        try:
            self.store.update_attempt(
                request_id,
                {"status": "BROKER_REQUEST_SENT"},
            )

            self.logger.info(
                "broker_order_request_sent",
                {
                    "request_id": request_id,
                    "idempotency_key": key,
                    "broker": broker_name,
                    "account_id": account_id,
                    "symbol": trade.symbol,
                    "action": trade.action,
                    "units": units,
                },
            )

            response = broker.place_order(
                symbol=trade.symbol,
                units=units,
                entry_price=trade.entry_price,
                take_profit=trade.take_profit,
                stop_loss=trade.stop_loss,
            )

            self.store.update_attempt(
                request_id,
                {
                    "status": "BROKER_RESPONSE_RECEIVED",
                    "raw_response": response,
                },
            )

            self.logger.info(
                "broker_response_received",
                {
                    "request_id": request_id,
                    "idempotency_key": key,
                    "response": response,
                },
            )

            result = self._parse_oanda_response(
                response=response,
                account_id=account_id,
                broker_name=broker_name,
                trade=trade,
                units=units,
            )

            self.store.update_attempt(
                request_id,
                {
                    "status": result.status.value,
                    "broker_trade_id": result.broker_trade_id,
                    "broker_order_id": result.broker_order_id,
                    "reason": result.reason,
                    "raw_response": response,
                },
            )

            self._append_execution_result_event(
                result=result,
                trade=trade,
                broker_name=broker_name,
                account_id=account_id,
            )

            result = self.reconciler.verify_execution(broker, result)

            if result.status == ExecutionStatus.DISCREPANCY:
                self.store.update_attempt(
                    request_id,
                    {
                        "status": ExecutionStatus.DISCREPANCY.value,
                        "reason": result.reason,
                    },
                )

                self.event_store.append(
                    TradeEvent(
                        event_type=TradeEventType.DISCREPANCY_DETECTED,
                        source=trade.source,
                        signal_id=trade.external_signal_id,
                        trade_id=result.broker_trade_id,
                        broker=broker_name,
                        account_id=account_id,
                        symbol=trade.symbol,
                        strategy=trade.strategy_account,
                        payload=result.__dict__,
                    )
                )

                self.logger.error("broker_state_discrepancy", result.__dict__)
                raise RuntimeError(result.reason)

            self.logger.info("trade_submission_finished", result.__dict__)
            return result

        except Exception as error:
            self.logger.error(
                "trade_execution_exception",
                {
                    "request_id": request_id,
                    "idempotency_key": key,
                    "broker": broker_name,
                    "account_id": account_id,
                    "symbol": trade.symbol,
                    "error": str(error),
                },
            )

            try:
                self.store.update_attempt(
                    request_id,
                    {
                        "status": "EXCEPTION",
                        "reason": str(error),
                    },
                )
            except Exception:
                pass

            raise

    def _append_execution_result_event(
        self,
        result,
        trade,
        broker_name: str,
        account_id: str,
    ):
        event_type = {
            ExecutionStatus.FILLED: TradeEventType.ORDER_FILLED,
            ExecutionStatus.CANCELED: TradeEventType.ORDER_CANCELED,
            ExecutionStatus.REJECTED: TradeEventType.ORDER_REJECTED,
        }.get(result.status)

        if not event_type:
            return

        self.event_store.append(
            TradeEvent(
                event_type=event_type,
                source=trade.source,
                signal_id=trade.external_signal_id,
                trade_id=result.broker_trade_id,
                broker=broker_name,
                account_id=account_id,
                symbol=trade.symbol,
                strategy=trade.strategy_account,
                payload=result.__dict__,
            )
        )

    def _parse_oanda_response(self, response, account_id, broker_name, trade, units):
        order_fill = response.get("orderFillTransaction")
        order_cancel = response.get("orderCancelTransaction")
        order_create = response.get("orderCreateTransaction")

        if order_fill:
            trade_opened = order_fill.get("tradeOpened") or {}

            return ExecutionResult(
                status=ExecutionStatus.FILLED,
                broker=broker_name,
                account_id=account_id,
                symbol=trade.symbol,
                action=trade.action,
                requested_units=units,
                broker_trade_id=trade_opened.get("tradeID"),
                broker_order_id=order_fill.get("orderID"),
                reason=order_fill.get("reason"),
                raw_response=response,
            )

        if order_cancel:
            return ExecutionResult(
                status=ExecutionStatus.CANCELED,
                broker=broker_name,
                account_id=account_id,
                symbol=trade.symbol,
                action=trade.action,
                requested_units=units,
                broker_order_id=order_cancel.get("orderID"),
                reason=order_cancel.get("reason"),
                raw_response=response,
            )

        if order_create:
            return ExecutionResult(
                status=ExecutionStatus.PENDING,
                broker=broker_name,
                account_id=account_id,
                symbol=trade.symbol,
                action=trade.action,
                requested_units=units,
                broker_order_id=order_create.get("id"),
                reason=order_create.get("reason"),
                raw_response=response,
            )

        return ExecutionResult(
            status=ExecutionStatus.UNKNOWN,
            broker=broker_name,
            account_id=account_id,
            symbol=trade.symbol,
            action=trade.action,
            requested_units=units,
            reason="Unknown broker response",
            raw_response=response,
        )

    def execute_request(self, request: ExecutionRequest):
        trade = self.request_adapter.to_trade_request(request)
        result = self.execute_trade(trade)

        return ContractExecutionResult(
            execution_request_id=request.id,
            status=self._map_execution_status(result.status),
            broker=result.broker,
            account_id=result.account_id,
            symbol=result.symbol,
            action=result.action,
            requested_units=result.requested_units,
            broker_trade_id=result.broker_trade_id,
            broker_order_id=result.broker_order_id,
            reason=result.reason,
            raw_response=result.raw_response,
        )

    def _map_execution_status(self, status: ExecutionStatus):
        mapping = {
            ExecutionStatus.FILLED: ContractExecutionStatus.FILLED,
            ExecutionStatus.CANCELED: ContractExecutionStatus.CANCELED,
            ExecutionStatus.REJECTED: ContractExecutionStatus.REJECTED,
            ExecutionStatus.PENDING: ContractExecutionStatus.PENDING,
            ExecutionStatus.DISCREPANCY: ContractExecutionStatus.DISCREPANCY,
            ExecutionStatus.UNKNOWN: ContractExecutionStatus.UNKNOWN,
        }

        return mapping.get(status, ContractExecutionStatus.UNKNOWN)
