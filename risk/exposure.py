from dataclasses import dataclass


@dataclass(frozen=True)
class OpenPosition:
    symbol: str
    source: str
    broker: str
    account_id: str
    units: int
    risk_amount: float
    opened_at: str | None = None


@dataclass(frozen=True)
class ExposureSnapshot:
    total_open_trades: int
    total_risk: float
    symbol_risk: dict[str, float]
    source_risk: dict[str, float]
    account_risk: dict[str, float]
    broker_risk: dict[str, float]


class ExposureRisk:
    def calculate(self, positions: list[OpenPosition]) -> ExposureSnapshot:
        symbol_risk: dict[str, float] = {}
        source_risk: dict[str, float] = {}
        account_risk: dict[str, float] = {}
        broker_risk: dict[str, float] = {}

        for position in positions:
            symbol_risk[position.symbol] = symbol_risk.get(position.symbol, 0.0) + position.risk_amount
            source_risk[position.source] = source_risk.get(position.source, 0.0) + position.risk_amount
            account_risk[position.account_id] = account_risk.get(position.account_id, 0.0) + position.risk_amount
            broker_risk[position.broker] = broker_risk.get(position.broker, 0.0) + position.risk_amount

        return ExposureSnapshot(
            total_open_trades=len(positions),
            total_risk=sum(position.risk_amount for position in positions),
            symbol_risk=symbol_risk,
            source_risk=source_risk,
            account_risk=account_risk,
            broker_risk=broker_risk,
        )
