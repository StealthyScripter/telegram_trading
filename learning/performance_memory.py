from dataclasses import dataclass


@dataclass(frozen=True)
class SourcePerformance:
    source: str
    trades: int
    wins: int
    losses: int
    net_r: float
    recent_net_r: float

    @property
    def win_rate(self) -> float:
        closed = self.wins + self.losses
        return self.wins / closed if closed else 0.0


@dataclass(frozen=True)
class TradeOutcome:
    source: str
    realized_r: float
    trade_id: str | None = None
    closed_at: str | None = None


class PerformanceMemory:
    def build(self, events: list[dict]) -> dict[str, SourcePerformance]:
        by_source: dict[str, list[float]] = {}

        for event in events:
            payload = event.get("payload") or {}
            source = (
                payload.get("source")
                or payload.get("source_name")
                or payload.get("profile", {}).get("source_name")
            )
            realized_r = payload.get("realized_r")
            if realized_r is None and payload.get("result"):
                realized_r = payload["result"].get("realized_r")
            if source is None or realized_r is None:
                continue
            by_source.setdefault(str(source), []).append(float(realized_r))

        return {
            source: self._performance(source, values)
            for source, values in by_source.items()
        }

    def ingest_outcome(
        self,
        existing: dict[str, SourcePerformance],
        outcome: TradeOutcome,
    ) -> dict[str, SourcePerformance]:
        if not outcome.source:
            raise ValueError("TradeOutcome.source is required")

        if not isinstance(outcome.realized_r, (int, float)):
            raise ValueError("TradeOutcome.realized_r must be numeric")

        values_by_source = {
            source: self._values_from_performance(performance)
            for source, performance in existing.items()
        }
        values_by_source.setdefault(outcome.source, []).append(float(outcome.realized_r))
        return {
            source: self._performance(source, values)
            for source, values in values_by_source.items()
        }

    def _performance(self, source: str, values: list[float]) -> SourcePerformance:
        recent = values[-5:]
        return SourcePerformance(
            source=source,
            trades=len(values),
            wins=len([value for value in values if value > 0]),
            losses=len([value for value in values if value < 0]),
            net_r=sum(values),
            recent_net_r=sum(recent),
        )

    def _values_from_performance(self, performance: SourcePerformance) -> list[float]:
        values = [1.0] * performance.wins
        values.extend([-1.0] * performance.losses)
        breakeven_count = max(0, performance.trades - performance.wins - performance.losses)
        values.extend([0.0] * breakeven_count)

        difference = round(performance.net_r - sum(values), 10)
        if values:
            values[-1] += difference
        elif performance.trades:
            values.append(performance.net_r)
        return values
