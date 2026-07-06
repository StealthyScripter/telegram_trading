from dataclasses import asdict

from controls.bot_controls import BotControls
from dashboard.models import Alert, BrokerHealth, OperationalEventType, PipelineStatus, ReconciliationStatus
from events.ledger import EventLedger
from events.models import DecisionEvent
from risk.portfolio import PortfolioState


class AlertSink:
    def __init__(self):
        self.alerts: list[Alert] = []

    def emit(self, alert: Alert):
        self.alerts.append(alert)


class OperationsDashboard:
    def __init__(
        self,
        ledger: EventLedger,
        controls: BotControls | None = None,
        alert_sink: AlertSink | None = None,
    ):
        self.ledger = ledger
        self.controls = controls or BotControls()
        self.alert_sink = alert_sink or AlertSink()

    def pipeline_status(self) -> PipelineStatus:
        kill_switch = self.controls.kill_switch_enabled()
        return PipelineStatus(
            status="blocked" if kill_switch else "ready",
            kill_switch_enabled=kill_switch,
            live_trading_allowed=self.controls.live_trading_allowed(),
            paper_mode_available=True,
        )

    def event_ledger_view(self, stage: str | None = None, limit: int | None = None) -> list[dict]:
        events = self.ledger.find_by_stage(stage) if stage else self.ledger.all_events()
        if limit is not None:
            return events[-limit:]
        return events

    def execution_state_view(self, execution_results: list[dict]) -> dict:
        return {
            "total_results": len(execution_results),
            "filled": len([item for item in execution_results if item.get("status") == "FILLED"]),
            "rejected": len([item for item in execution_results if item.get("status") == "REJECTED"]),
            "results": list(execution_results),
        }

    def broker_health_view(self, broker) -> BrokerHealth:
        try:
            open_trades = broker.get_open_trades()
            return BrokerHealth(
                broker=broker.__class__.__name__,
                account_id=getattr(broker, "account_id", None),
                env=getattr(broker, "env", None),
                healthy=True,
                open_trade_count=len(open_trades),
            )
        except Exception as error:
            return BrokerHealth(
                broker=broker.__class__.__name__,
                account_id=getattr(broker, "account_id", None),
                env=getattr(broker, "env", None),
                healthy=False,
                reason=str(error),
            )

    def channel_profile_view(self, store) -> list[dict]:
        return [profile.to_dict() for profile in store.all_profiles()]

    def risk_exposure_view(self, portfolio_state: PortfolioState) -> dict:
        exposure = portfolio_state.exposure()
        return {
            "open_trades": len(portfolio_state.open_positions),
            "daily_risk_used": portfolio_state.daily_risk_used,
            "weekly_risk_used": portfolio_state.weekly_risk_used,
            "total_open_risk": exposure.total_risk,
            "symbol_risk": dict(exposure.symbol_risk),
            "source_risk": dict(exposure.source_risk),
            "account_risk": dict(exposure.account_risk),
            "currency_risk": dict(exposure.currency_risk),
            "strategy_risk": dict(exposure.strategy_risk),
            "correlation_risk": dict(exposure.correlation_risk),
            "current_drawdown": portfolio_state.current_drawdown,
        }

    def reconciliation_status(
        self,
        expected_open_trades: int,
        actual_open_trades: int,
    ) -> ReconciliationStatus:
        drift = expected_open_trades != actual_open_trades
        return ReconciliationStatus(
            drift_detected=drift,
            expected_open_trades=expected_open_trades,
            actual_open_trades=actual_open_trades,
            reason="Drift detected" if drift else "Execution state reconciled",
        )

    def paper_live_mode_view(self) -> dict:
        return {
            "paper_enabled": True,
            "live_enabled": self.controls.live_trading_allowed(),
            "kill_switch_enabled": self.controls.kill_switch_enabled(),
        }

    def emit_alert(self, alert: Alert):
        self.alert_sink.emit(alert)
        self.ledger.append(
            DecisionEvent(
                stage="operations",
                input_id=alert.severity,
                output_id=None,
                reason=alert.message,
                payload={
                    "event_type": OperationalEventType.ALERT_EMITTED.value,
                    "alert": asdict(alert),
                },
            )
        )


class OperationalControlService:
    def __init__(self, ledger: EventLedger):
        self.ledger = ledger

    def record_kill_switch_control(
        self,
        enabled: bool,
        actor: str,
        reason: str,
    ) -> dict:
        payload = {
            "event_type": OperationalEventType.KILL_SWITCH_CONTROL_RECORDED.value,
            "enabled": enabled,
            "actor": actor,
            "reason": reason,
        }
        self.ledger.append(
            DecisionEvent(
                stage="operations",
                input_id=actor,
                output_id=None,
                reason=reason,
                payload=payload,
            )
        )
        return payload
