from dataclasses import dataclass
from enum import Enum

from learning.performance_memory import SourcePerformance


class SourceHealth(str, Enum):
    IMPROVING = "improving"
    DETERIORATING = "deteriorating"
    STABLE = "stable"


@dataclass(frozen=True)
class SourceEvaluation:
    source: str
    health: SourceHealth
    reason: str


class SourceEvaluator:
    def evaluate(self, performance: SourcePerformance) -> SourceEvaluation:
        if performance.trades == 0:
            return SourceEvaluation(performance.source, SourceHealth.STABLE, "No trades")

        if performance.recent_net_r < 0 and performance.net_r <= 0:
            return SourceEvaluation(
                performance.source,
                SourceHealth.DETERIORATING,
                "Recent and total performance are negative",
            )

        if performance.recent_net_r > 0 and performance.net_r > 0:
            return SourceEvaluation(
                performance.source,
                SourceHealth.IMPROVING,
                "Recent and total performance are positive",
            )

        return SourceEvaluation(performance.source, SourceHealth.STABLE, "Mixed performance")
