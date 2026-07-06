import json

import pytest

from contracts.execution_request import ExecutionRequest
from controls.bot_controls import BotControls
from deployment.readiness import (
    BackupManager,
    DryRunExecutionService,
    EnvironmentValidator,
    LiveTradingGuard,
    ProductionReadinessChecklist,
    StartupRecoveryValidator,
)


def test_missing_required_secret_blocks_live_startup():
    result = EnvironmentValidator().validate(
        env={"OANDA_ENV": "live"},
        mode="live",
    )

    assert result.passed is False
    assert "OANDA_API_TOKEN" in result.missing


def test_invalid_environment_blocks_startup():
    result = EnvironmentValidator().validate(env={}, mode="invalid")

    assert result.passed is False
    assert result.reason == "Invalid mode: invalid"


def test_paper_mode_can_start_without_live_secrets():
    result = EnvironmentValidator().validate(env={}, mode="paper")

    assert result.passed is True


def test_dry_run_mode_does_not_execute_real_orders():
    request = ExecutionRequest(
        capital_allocation_id="capital-1",
        source="pytest",
        broker="oanda",
        symbol="EUR_USD",
        action="buy",
        units=100,
    )

    result = DryRunExecutionService().execute(request)

    assert result["dry_run"] is True
    assert result["executed"] is False
    assert result["execution_request_id"] == request.id


def test_live_guard_blocks_without_explicit_approval():
    with pytest.raises(RuntimeError, match="LIVE_TRADING_APPROVED"):
        LiveTradingGuard().assert_live_allowed(
            {"ALLOW_LIVE_TRADING": "true", "LIVE_TRADING_APPROVED": "false"}
        )


def test_live_guard_allows_only_with_explicit_approval():
    LiveTradingGuard().assert_live_allowed(
        {"ALLOW_LIVE_TRADING": "true", "LIVE_TRADING_APPROVED": "true"}
    )


def test_kill_switch_blocks_execution(monkeypatch):
    monkeypatch.setenv("BOT_KILL_SWITCH", "true")

    with pytest.raises(RuntimeError, match="BOT_KILL_SWITCH"):
        LiveTradingGuard(controls=BotControls()).assert_execution_allowed("paper")


def test_startup_recovery_validates_prior_state(tmp_path):
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"attempts": []}), encoding="utf-8")

    result = StartupRecoveryValidator().validate_state_file(str(state_path))

    assert result.passed is True


def test_startup_recovery_rejects_invalid_state(tmp_path):
    state_path = tmp_path / "state.json"
    state_path.write_text("{bad", encoding="utf-8")

    result = StartupRecoveryValidator().validate_state_file(str(state_path))

    assert result.passed is False
    assert "invalid JSON" in result.reason


def test_backup_routine_produces_artifact_and_metadata(tmp_path):
    source = tmp_path / "state.json"
    source.write_text(json.dumps({"attempts": []}), encoding="utf-8")

    metadata = BackupManager().create_backup(str(source), str(tmp_path / "backups"))

    assert metadata["exists"] is True
    assert metadata["size_bytes"] > 0


def test_restore_validation_checks_artifact(tmp_path):
    backup = tmp_path / "state.json.bak"
    backup.write_text("{}", encoding="utf-8")

    result = BackupManager().validate_restore(str(backup))

    assert result.passed is True


def test_rollback_and_incident_playbook_documentation_exists():
    docs = open("docs/production_readiness.md", encoding="utf-8").read()

    assert "Rollback Procedure" in docs
    assert "Incident Playbook" in docs


def test_production_readiness_checklist_fails_when_gate_missing():
    result = ProductionReadinessChecklist().evaluate({"safe_tests_passed": True})

    assert result.passed is False
    assert "integration_opt_in" in result.missing


def test_production_readiness_checklist_passes_only_when_all_gates_satisfied():
    checklist = ProductionReadinessChecklist()

    result = checklist.evaluate({gate: True for gate in checklist.required_gates})

    assert result.passed is True
