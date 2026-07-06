import inspect
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus
from decision import ensemble as ensemble_module
from decision.ensemble import EnsembleConfig, EnsembleDecisionEngine, EnsembleEventType
from events.ledger import EventLedger


def candidate(source="alpha", action="buy", symbol="EUR_USD", **overrides):
    data = {
        "parsed_signal_id": f"parsed-{source}",
        "source": source,
        "status": TradeCandidateStatus.APPROVED_FOR_RISK,
        "symbol": symbol,
        "action": action,
        "entry_price": "1.1000",
        "stop_loss": "1.0950",
        "take_profits": ["1.1100"],
        "confidence": 0.9,
    }
    data.update(overrides)
    return TradeCandidate(**data)


def engine(tmp_path, config=None, source_scores=None):
    return EnsembleDecisionEngine(
        config=config or EnsembleConfig(),
        ledger=EventLedger(path=str(tmp_path / "ensemble_ledger.json")),
        source_scores=source_scores,
    )


def test_single_source_pass_through(tmp_path):
    decision = engine(tmp_path).evaluate([candidate()])

    assert decision.approved is True
    assert decision.candidate.symbol == "EUR_USD"
    assert decision.consensus_score.score == 1.0


def test_multi_source_agreement(tmp_path):
    decision = engine(tmp_path).evaluate([
        candidate("alpha"),
        candidate("beta"),
    ])

    assert decision.approved is True
    assert decision.consensus_score.source_count == 2


def test_buy_sell_conflict_rejected(tmp_path):
    decision = engine(tmp_path).evaluate([
        candidate("alpha", "buy"),
        candidate("beta", "sell"),
    ])

    assert decision.approved is False
    assert decision.conflict.conflict_detected is True
    assert "Conflicting" in decision.reason


def test_source_weighting_can_approve_majority(tmp_path):
    weighted = engine(
        tmp_path,
        config=EnsembleConfig(consensus_threshold=0.7, conflict_threshold=0.2),
        source_scores={"alpha": 100, "beta": 20},
    )

    decision = weighted.evaluate([
        candidate("alpha", "buy"),
        candidate("beta", "buy"),
    ])

    assert decision.approved is True
    assert decision.consensus_score.score == 1.0


def test_low_confidence_rejected(tmp_path):
    decision = engine(
        tmp_path,
        config=EnsembleConfig(minimum_confidence=0.8),
    ).evaluate([candidate(confidence=0.2)])

    assert decision.approved is False
    assert decision.reason == "No eligible candidates"


def test_stale_signal_ignored(tmp_path):
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()

    decision = engine(
        tmp_path,
        config=EnsembleConfig(max_signal_age_seconds=30),
    ).evaluate([candidate(created_at=old_time)])

    assert decision.approved is False
    assert decision.ensemble.ignored_candidate_ids


def test_duplicate_source_ignored(tmp_path):
    decision = engine(tmp_path).evaluate([
        candidate("alpha", parsed_signal_id="one"),
        candidate("alpha", parsed_signal_id="two"),
    ])

    assert decision.approved is True
    assert len(decision.ensemble.votes) == 1
    assert len(decision.ensemble.ignored_candidate_ids) == 1


def test_ledger_events_emitted(tmp_path):
    ensemble = engine(tmp_path)

    ensemble.evaluate([candidate("alpha"), candidate("beta")])

    event_types = [
        event["payload"]["event_type"]
        for event in ensemble.ledger.all_events()
    ]

    assert EnsembleEventType.ENSEMBLE_CREATED.value in event_types
    assert EnsembleEventType.ENSEMBLE_APPROVED.value in event_types


def test_ensemble_decision_is_immutable(tmp_path):
    decision = engine(tmp_path).evaluate([candidate()])

    with pytest.raises(FrozenInstanceError):
        decision.reason = "changed"


def test_ensemble_has_no_broker_or_execution_imports():
    source = inspect.getsource(ensemble_module)

    for forbidden in ["TradeExecutor", "BrokerFactory", "OandaBroker", "PaperBroker"]:
        assert forbidden not in source
