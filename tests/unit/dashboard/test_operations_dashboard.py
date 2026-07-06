import inspect

import pytest

from controls.bot_controls import BotControls
from dashboard import operations as operations_module
from dashboard.models import Alert, OperationalEventType
from dashboard.operations import AlertSink, OperationalControlService, OperationsDashboard
from decision.channel_intelligence import ChannelGrade, ChannelProfile, ChannelProfileStore
from events.ledger import EventLedger
from events.models import DecisionEvent
from risk.exposure import OpenPosition
from risk.portfolio import PortfolioState


class FakeBroker:
    env = "paper"
    account_id = "paper-1"

    def __init__(self, open_trades=None):
        self.open_trades = open_trades or []

    def get_open_trades(self):
        return list(self.open_trades)


def dashboard(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_KILL_SWITCH", "false")
    monkeypatch.setenv("ALLOW_LIVE_TRADING", "false")
    return OperationsDashboard(
        ledger=EventLedger(path=str(tmp_path / "operations.json")),
        controls=BotControls(),
    )


def test_pipeline_status_view_reports_modes(tmp_path, monkeypatch):
    view = dashboard(tmp_path, monkeypatch).pipeline_status()

    assert view.status == "ready"
    assert view.kill_switch_enabled is False
    assert view.live_trading_allowed is False
    assert view.paper_mode_available is True


def test_event_ledger_view_reads_without_mutation(tmp_path, monkeypatch):
    ops = dashboard(tmp_path, monkeypatch)
    ops.ledger.append(
        DecisionEvent(stage="decision", input_id="in", output_id="out", reason="ok")
    )

    before = ops.ledger.all_events()
    view = ops.event_ledger_view(stage="decision")
    after = ops.ledger.all_events()

    assert view == before
    assert after == before


def test_execution_state_view_returns_expected_state(tmp_path, monkeypatch):
    view = dashboard(tmp_path, monkeypatch).execution_state_view(
        [
            {"status": "FILLED"},
            {"status": "REJECTED"},
        ]
    )

    assert view["total_results"] == 2
    assert view["filled"] == 1
    assert view["rejected"] == 1


def test_broker_health_view_uses_abstraction(tmp_path, monkeypatch):
    view = dashboard(tmp_path, monkeypatch).broker_health_view(
        FakeBroker(open_trades=[{"id": "1"}])
    )

    assert view.healthy is True
    assert view.env == "paper"
    assert view.account_id == "paper-1"
    assert view.open_trade_count == 1


def test_channel_profile_view_returns_profiles(tmp_path, monkeypatch):
    store = ChannelProfileStore(path=str(tmp_path / "profiles.json"))
    store.save(
        ChannelProfile(
            source_name="alpha",
            first_seen="2026-01-01T00:00:00+00:00",
            last_seen="2026-01-01T00:00:00+00:00",
            score=80,
            grade=ChannelGrade.LIVE,
        )
    )

    profiles = dashboard(tmp_path, monkeypatch).channel_profile_view(store)

    assert profiles[0]["source_name"] == "alpha"
    assert profiles[0]["grade"] == ChannelGrade.LIVE.value


def test_risk_exposure_view_returns_aggregate_exposure(tmp_path, monkeypatch):
    state = PortfolioState(
        account_id="acct-1",
        broker="paper",
        equity=10000,
        open_positions=[
            OpenPosition(
                symbol="EUR_USD",
                source="alpha",
                broker="paper",
                account_id="paper",
                units=1000,
                risk_amount=10,
                currency="EUR",
                strategy="scalping",
                correlation_group="EUR",
            )
        ],
        daily_risk_used=10,
        weekly_risk_used=20,
        current_drawdown=3,
    )

    view = dashboard(tmp_path, monkeypatch).risk_exposure_view(state)

    assert view["total_open_risk"] == 10
    assert view["symbol_risk"] == {"EUR_USD": 10}
    assert view["current_drawdown"] == 3


def test_kill_switch_control_emits_audit_event(tmp_path):
    ledger = EventLedger(path=str(tmp_path / "operations.json"))

    payload = OperationalControlService(ledger=ledger).record_kill_switch_control(
        enabled=True,
        actor="operator",
        reason="incident",
    )

    assert payload["enabled"] is True
    assert ledger.latest(1)[0]["payload"]["event_type"] == OperationalEventType.KILL_SWITCH_CONTROL_RECORDED.value


def test_kill_switch_blocks_execution_control(monkeypatch):
    monkeypatch.setenv("BOT_KILL_SWITCH", "true")

    with pytest.raises(RuntimeError, match="BOT_KILL_SWITCH"):
        BotControls().assert_can_trade("paper")


def test_paper_live_mode_view_is_clear(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_KILL_SWITCH", "false")
    monkeypatch.setenv("ALLOW_LIVE_TRADING", "true")

    view = OperationsDashboard(
        ledger=EventLedger(path=str(tmp_path / "operations.json")),
        controls=BotControls(),
    ).paper_live_mode_view()

    assert view == {
        "paper_enabled": True,
        "live_enabled": True,
        "kill_switch_enabled": False,
    }


def test_reconciliation_status_reports_drift(tmp_path, monkeypatch):
    view = dashboard(tmp_path, monkeypatch).reconciliation_status(
        expected_open_trades=2,
        actual_open_trades=1,
    )

    assert view.drift_detected is True
    assert view.reason == "Drift detected"


def test_dashboard_does_not_import_execution_service_or_brokers():
    source = inspect.getsource(operations_module)

    for forbidden in ["ExecutionService", "TradeExecutor", "OandaBroker", "PaperBroker"]:
        assert forbidden not in source


def test_alerting_hook_receives_operational_events(tmp_path, monkeypatch):
    ledger = EventLedger(path=str(tmp_path / "operations.json"))
    sink = AlertSink()
    ops = OperationsDashboard(ledger=ledger, alert_sink=sink)

    ops.emit_alert(Alert(severity="warning", message="reconciliation drift"))

    assert sink.alerts[0].message == "reconciliation drift"
    assert ledger.latest(1)[0]["payload"]["event_type"] == OperationalEventType.ALERT_EMITTED.value
