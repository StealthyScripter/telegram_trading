from learning.performance_memory import PerformanceMemory


def test_builds_memory_from_sample_events():
    events = [
        {"payload": {"source": "alpha", "realized_r": 1.0}},
        {"payload": {"source": "alpha", "realized_r": -0.5}},
        {"payload": {"source": "beta", "realized_r": 2.0}},
    ]

    memory = PerformanceMemory().build(events)

    assert memory["alpha"].trades == 2
    assert memory["alpha"].wins == 1
    assert memory["alpha"].losses == 1
    assert memory["alpha"].net_r == 0.5
    assert memory["beta"].win_rate == 1.0
