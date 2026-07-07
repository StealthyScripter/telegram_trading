import time
import uuid
from datetime import datetime, timezone

from controls.bot_controls import BotControls
from data.execution_store import ExecutionStore
from events.event_store import EventStore
from events.trade_event import TradeEvent, TradeEventType
from execution.brokers.factory import BrokerFactory
from monitoring.logger import ExecutionLogger


class CloseExecutor:
    def __init__(self):
        self.broker_factory = BrokerFactory()
        self.bot_controls = BotControls()
        self.store = ExecutionStore()
        self.logger = ExecutionLogger()
        self.event_store = EventStore()

    def close_trade(
        self,
        broker_name: str,
        account_id: str,
        trade_id: str,
        symbol: str | None = None,
        reason: str = "manual_close",
        verify_retries: int = 5,
        verify_sleep_seconds: float = 1.0,
    ):
        request_id = f"close-{trade_id}-{uuid.uuid4()}"

        broker = self.broker_factory.create(
            broker_name=broker_name,
            account_id=account_id,
        )

        self.bot_controls.assert_can_trade(broker.env)

        payload = {
            "request_id": request_id,
            "broker": broker_name,
            "broker_env": broker.env,
            "account_id": account_id,
            "symbol": symbol,
            "broker_trade_id": trade_id,
            "reason": reason,
        }

        self.store.create_close_attempt(request_id, payload)
        self.logger.info("close_attempt_started", payload)

        self.event_store.append(
            TradeEvent(
                event_type=TradeEventType.TRADE_CLOSE_REQUESTED,
                trade_id=trade_id,
                broker=broker_name,
                account_id=account_id,
                symbol=symbol,
                payload=payload,
            )
        )

        try:
            self.store.update_close_attempt(
                request_id,
                {"status": "CLOSE_REQUEST_SENT"},
            )

            response = broker.close_trade(trade_id)

            self.store.update_close_attempt(
                request_id,
                {
                    "status": "CLOSE_RESPONSE_RECEIVED",
                    "raw_response": response,
                },
            )

            is_still_open = self._verify_trade_still_open_with_retries(
                broker=broker,
                trade_id=trade_id,
                retries=verify_retries,
                sleep_seconds=verify_sleep_seconds,
            )

            if is_still_open:
                discrepancy_reason = (
                    "Trade close response received but broker trade still exists after retries"
                )

                self.store.update_close_attempt(
                    request_id,
                    {
                        "status": "DISCREPANCY",
                        "reason": discrepancy_reason,
                        "raw_response": response,
                    },
                )

                self.event_store.append(
                    TradeEvent(
                        event_type=TradeEventType.DISCREPANCY_DETECTED,
                        trade_id=trade_id,
                        broker=broker_name,
                        account_id=account_id,
                        symbol=symbol,
                        payload={
                            "reason": discrepancy_reason,
                            "raw_response": response,
                        },
                    )
                )

                self.logger.error(
                    "close_discrepancy_trade_still_open",
                    {
                        "request_id": request_id,
                        "broker": broker_name,
                        "account_id": account_id,
                        "trade_id": trade_id,
                        "response": response,
                    },
                )

                raise RuntimeError(
                    "Close discrepancy: broker trade still exists after retries"
                )

            order_fill = response.get("orderFillTransaction", {})
            trades_closed = order_fill.get("tradesClosed", [])
            first_closed = trades_closed[0] if trades_closed else {}

            close_payload = {
                "status": "CLOSED",
                "reason": order_fill.get("reason"),
                "close_price": first_closed.get("price"),
                "realized_pl": first_closed.get("realizedPL"),
                "closed_at": datetime.now(timezone.utc).isoformat(),
                "raw_response": response,
            }

            self.store.update_close_attempt(request_id, close_payload)

            self.event_store.append(
                TradeEvent(
                    event_type=TradeEventType.TRADE_CLOSED,
                    trade_id=trade_id,
                    broker=broker_name,
                    account_id=account_id,
                    symbol=symbol,
                    payload=close_payload,
                )
            )

            self.logger.info(
                "trade_close_finished",
                {
                    "request_id": request_id,
                    "broker": broker_name,
                    "account_id": account_id,
                    "trade_id": trade_id,
                    "response": response,
                },
            )

            return response

        except Exception as error:
            self.store.update_close_attempt(
                request_id,
                {
                    "status": "EXCEPTION",
                    "reason": str(error),
                },
            )

            self.logger.error(
                "trade_close_exception",
                {
                    "request_id": request_id,
                    "broker": broker_name,
                    "account_id": account_id,
                    "trade_id": trade_id,
                    "error": str(error),
                },
            )

            raise

    def _verify_trade_still_open_with_retries(
        self,
        broker,
        trade_id: str,
        retries: int,
        sleep_seconds: float,
    ) -> bool:
        for _ in range(retries):
            time.sleep(sleep_seconds)

            trade = broker.get_trade(trade_id)

            if not trade:
                return False

            state = trade.get("state")

            if state and state.upper() != "OPEN":
                return False

        return True
