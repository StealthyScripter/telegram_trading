from dataclasses import dataclass, field
from enum import Enum


class OperationalEventType(str, Enum):
    KILL_SWITCH_CONTROL_RECORDED = "KILL_SWITCH_CONTROL_RECORDED"
    ALERT_EMITTED = "ALERT_EMITTED"


@dataclass(frozen=True)
class PipelineStatus:
    status: str
    kill_switch_enabled: bool
    live_trading_allowed: bool
    paper_mode_available: bool = True


@dataclass(frozen=True)
class BrokerHealth:
    broker: str
    account_id: str | None
    env: str | None
    healthy: bool
    open_trade_count: int = 0
    reason: str | None = None


@dataclass(frozen=True)
class ReconciliationStatus:
    drift_detected: bool
    expected_open_trades: int
    actual_open_trades: int
    reason: str


@dataclass(frozen=True)
class Alert:
    severity: str
    message: str
    metadata: dict = field(default_factory=dict)
