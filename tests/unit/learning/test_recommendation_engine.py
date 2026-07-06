import inspect

from events.ledger import EventLedger
from learning import recommendation_engine as recommendation_module
from learning.recommendation_engine import LearningEventType, RecommendationEngine, RecommendationType
from learning.source_evaluator import SourceEvaluation, SourceHealth


def test_creates_advisory_recommendation(tmp_path):
    engine = RecommendationEngine(ledger=EventLedger(path=str(tmp_path / "learning.json")))

    recommendation = engine.recommend(
        SourceEvaluation("alpha", SourceHealth.DETERIORATING, "bad recent performance")
    )

    assert recommendation.recommendation == RecommendationType.PAUSE
    assert recommendation.advisory_only is True


def test_ledger_events_emitted(tmp_path):
    engine = RecommendationEngine(ledger=EventLedger(path=str(tmp_path / "learning.json")))

    engine.recommend(
        SourceEvaluation("alpha", SourceHealth.IMPROVING, "improving")
    )

    event_types = [event["payload"]["event_type"] for event in engine.ledger.all_events()]

    assert LearningEventType.SOURCE_IMPROVEMENT_DETECTED.value in event_types
    assert LearningEventType.LEARNING_RECOMMENDATION_CREATED.value in event_types


def test_learning_has_no_execution_or_broker_imports():
    source = inspect.getsource(recommendation_module)

    for forbidden in ["TradeExecutor", "BrokerFactory", "OandaBroker", "PaperBroker"]:
        assert forbidden not in source
