import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from controls.bot_controls import BotControls


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    reason: str
    missing: tuple[str, ...] = field(default_factory=tuple)


class EnvironmentValidator:
    live_required = (
        "OANDA_API_TOKEN",
        "OANDA_ACCOUNT_ID",
        "OANDA_ENV",
        "ALLOW_LIVE_TRADING",
        "LIVE_TRADING_APPROVED",
    )

    def validate(self, env: dict[str, str], mode: str) -> ValidationResult:
        if mode not in {"paper", "live", "dry_run"}:
            return ValidationResult(False, f"Invalid mode: {mode}")

        if mode in {"paper", "dry_run"}:
            return ValidationResult(True, "Paper/dry-run mode does not require live secrets")

        missing = tuple(name for name in self.live_required if not env.get(name))
        if missing:
            return ValidationResult(False, "Missing required live secrets", missing)

        if env.get("OANDA_ENV") != "live":
            return ValidationResult(False, "Live startup requires OANDA_ENV=live")

        if env.get("ALLOW_LIVE_TRADING", "false").lower() != "true":
            return ValidationResult(False, "Live trading flag is not enabled")

        if env.get("LIVE_TRADING_APPROVED", "false").lower() != "true":
            return ValidationResult(False, "Explicit live approval is required")

        return ValidationResult(True, "Live environment validated")


class LiveTradingGuard:
    def __init__(self, controls: BotControls | None = None):
        self.controls = controls or BotControls()

    def assert_live_allowed(self, env: dict[str, str]):
        if env.get("LIVE_TRADING_APPROVED", "false").lower() != "true":
            raise RuntimeError("Live trading requires explicit LIVE_TRADING_APPROVED=true")

        if env.get("ALLOW_LIVE_TRADING", "false").lower() != "true":
            raise RuntimeError("Live trading requires ALLOW_LIVE_TRADING=true")

    def assert_execution_allowed(self, broker_env: str):
        self.controls.assert_can_trade(broker_env)


class DryRunExecutionService:
    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return {
            "dry_run": True,
            "executed": False,
            "execution_request_id": getattr(request, "id", None),
            "broker": getattr(request, "broker", None),
            "symbol": getattr(request, "symbol", None),
        }


class StartupRecoveryValidator:
    def validate_state_file(self, path: str) -> ValidationResult:
        state_path = Path(path)
        if not state_path.exists():
            return ValidationResult(False, "State file is missing")

        try:
            with state_path.open("r", encoding="utf-8") as file:
                json.load(file)
        except json.JSONDecodeError as error:
            return ValidationResult(False, f"State file is invalid JSON: {error}")

        return ValidationResult(True, "State file validated")


class BackupManager:
    def create_backup(self, source_path: str, backup_dir: str) -> dict:
        source = Path(source_path)
        destination_dir = Path(backup_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / f"{source.name}.bak"
        shutil.copy2(source, destination)
        return {
            "source": str(source),
            "backup_path": str(destination),
            "exists": destination.exists(),
            "size_bytes": destination.stat().st_size,
        }

    def validate_restore(self, backup_path: str) -> ValidationResult:
        path = Path(backup_path)
        if not path.exists():
            return ValidationResult(False, "Backup artifact is missing")

        if path.stat().st_size <= 0:
            return ValidationResult(False, "Backup artifact is empty")

        return ValidationResult(True, "Backup artifact validated")


class ProductionReadinessChecklist:
    required_gates = (
        "safe_tests_passed",
        "integration_opt_in",
        "kill_switch_verified",
        "live_guard_verified",
        "backup_verified",
        "rollback_documented",
        "incident_playbook_documented",
        "monitoring_verified",
    )

    def evaluate(self, gates: dict[str, bool]) -> ValidationResult:
        missing = tuple(name for name in self.required_gates if not gates.get(name))
        if missing:
            return ValidationResult(False, "Production readiness gates missing", missing)
        return ValidationResult(True, "Production readiness gates satisfied")
