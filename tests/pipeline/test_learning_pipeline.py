from events.ledger import EventLedger
from learning.model_training_dataset import ModelTrainingDataset
from learning.performance_memory import PerformanceMemory
from learning.recommendation_engine import RecommendationEngine, RecommendationType
from learning.source_evaluator import SourceEvaluator


def test_learning_pipeline_recommends_pause_for_deterioration(tmp_path):
    events = [
        {"payload": {"source": "alpha", "realized_r": -1.0}},
        {"payload": {"source": "alpha", "realized_r": -0.5}},
    ]
    memory = PerformanceMemory().build(events)
    evaluation = SourceEvaluator().evaluate(memory["alpha"])
    recommendation_engine = RecommendationEngine(
        ledger=EventLedger(path=str(tmp_path / "learning.json"))
    )

    recommendation = recommendation_engine.recommend(evaluation)

    assert recommendation.recommendation == RecommendationType.PAUSE
    assert recommendation.advisory_only is True
    assert recommendation_engine.ledger.find_by_stage("learning")


def test_learning_pipeline_creates_training_dataset(tmp_path):
    events = [
        {"payload": {"source": "alpha", "realized_r": 1.0}},
    ]
    dataset = ModelTrainingDataset(ledger=EventLedger(path=str(tmp_path / "dataset.json")))

    examples = dataset.from_events(events)

    assert len(examples) == 1
    assert examples[0].source == "alpha"
    assert dataset.ledger.find_by_stage("learning")
