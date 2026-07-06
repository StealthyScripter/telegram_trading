from learning.performance_memory import SourcePerformance
from learning.source_evaluator import SourceEvaluator, SourceHealth


def test_detects_deteriorating_source():
    evaluation = SourceEvaluator().evaluate(
        SourcePerformance("alpha", trades=5, wins=1, losses=4, net_r=-2, recent_net_r=-1)
    )

    assert evaluation.health == SourceHealth.DETERIORATING


def test_detects_improving_source():
    evaluation = SourceEvaluator().evaluate(
        SourcePerformance("alpha", trades=5, wins=4, losses=1, net_r=3, recent_net_r=2)
    )

    assert evaluation.health == SourceHealth.IMPROVING
