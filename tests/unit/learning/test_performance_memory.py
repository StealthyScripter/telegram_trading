from learning.performance_memory import PerformanceMemory, TradeOutcome


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


def test_ingests_trade_closed_outcome_deterministically():
    memory_builder = PerformanceMemory()
    existing = memory_builder.build([
        {"payload": {"source": "alpha", "realized_r": 1.0}},
    ])

    first = memory_builder.ingest_outcome(existing, TradeOutcome(source="alpha", realized_r=-0.5))
    second = memory_builder.ingest_outcome(existing, TradeOutcome(source="alpha", realized_r=-0.5))

    assert first == second
    assert first["alpha"].trades == 2
    assert first["alpha"].wins == 1
    assert first["alpha"].losses == 1
    assert first["alpha"].net_r == 0.5
