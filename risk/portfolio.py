from dataclasses import dataclass, field

from risk.exposure import ExposureRisk, ExposureSnapshot, OpenPosition


@dataclass(frozen=True)
class PortfolioState:
    account_id: str
    broker: str
    equity: float
    open_positions: list[OpenPosition] = field(default_factory=list)
    daily_risk_used: float = 0.0
    weekly_risk_used: float = 0.0
    current_drawdown: float = 0.0

    def exposure(self) -> ExposureSnapshot:
        return ExposureRisk().calculate(self.open_positions)


@dataclass(frozen=True)
class RiskPolicy:
    max_open_trades: int = 10
    max_daily_risk: float = 500.0
    max_weekly_risk: float = 1500.0
    max_source_exposure: float = 500.0
    max_symbol_exposure: float = 500.0
    max_account_exposure: float = 1000.0
    max_broker_exposure: float = 1000.0
    max_correlated_exposure: float = 1000.0
    max_currency_exposure: float = 1000.0
    max_strategy_exposure: float = 1000.0
    max_drawdown: float = 1000.0
    max_risk_percent: float = 0.01


class PortfolioRisk:
    def snapshot(self, state: PortfolioState) -> ExposureSnapshot:
        return state.exposure()
