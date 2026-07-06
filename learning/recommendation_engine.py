from dataclasses import dataclass
from enum import Enum
from uuid import uuid4

from events.ledger import EventLedger
from events.models import DecisionEvent
from learning.source_evaluator import SourceEvaluation, SourceHealth


class LearningEventType(str, Enum):
    LEARNING_RECOMMENDATION_CREATED = "LEARNING_RECOMMENDATION_CREATED"
    SOURCE_DETERIORATION_DETECTED = "SOURCE_DETERIORATION_DETECTED"
    SOURCE_IMPROVEMENT_DETECTED = "SOURCE_IMPROVEMENT_DETECTED"


class RecommendationType(str, Enum):
    PROMOTE = "promote"
    DEMOTE = "demote"
    PAUSE = "pause"
    CONTINUE_PAPER = "continue_paper"
    INCREASE_ALLOCATION = "increase_allocation"
    DECREASE_ALLOCATION = "decrease_allocation"


@dataclass(frozen=True)
class LearningRecommendation:
    source: str
    recommendation: RecommendationType
    reason: str
    advisory_only: bool = True
    id: str = ""

    def __post_init__(self):
        if not self.id:
            object.__setattr__(self, "id", str(uuid4()))


class RecommendationEngine:
    def __init__(self, ledger: EventLedger | None = None):
        self.ledger = ledger or EventLedger()

    def recommend(self, evaluation: SourceEvaluation) -> LearningRecommendation:
        if evaluation.health == SourceHealth.DETERIORATING:
            recommendation = LearningRecommendation(
                source=evaluation.source,
                recommendation=RecommendationType.PAUSE,
                reason=evaluation.reason,
            )
            self._emit(LearningEventType.SOURCE_DETERIORATION_DETECTED, recommendation)
        elif evaluation.health == SourceHealth.IMPROVING:
            recommendation = LearningRecommendation(
                source=evaluation.source,
                recommendation=RecommendationType.PROMOTE,
                reason=evaluation.reason,
            )
            self._emit(LearningEventType.SOURCE_IMPROVEMENT_DETECTED, recommendation)
        else:
            recommendation = LearningRecommendation(
                source=evaluation.source,
                recommendation=RecommendationType.CONTINUE_PAPER,
                reason=evaluation.reason,
            )

        self._emit(LearningEventType.LEARNING_RECOMMENDATION_CREATED, recommendation)
        return recommendation

    def _emit(
        self,
        event_type: LearningEventType,
        recommendation: LearningRecommendation,
    ):
        self.ledger.append(
            DecisionEvent(
                stage="learning",
                input_id=recommendation.source,
                output_id=recommendation.id,
                reason=recommendation.reason,
                payload={
                    "event_type": event_type.value,
                    "source": recommendation.source,
                    "recommendation": recommendation.recommendation.value,
                    "advisory_only": recommendation.advisory_only,
                },
            )
        )
