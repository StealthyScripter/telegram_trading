import inspect

from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus
from decision import strategy_fusion as fusion_module
from decision.strategy_fusion import (
    SignalSourceType,
    StrategyFusionEngine,
    StrategyFusionEventType,
    StrategySignal,
)
from events.ledger import EventLedger


def candidate(source="alpha", action="buy", status=TradeCandidateStatus.APPROVED_FOR_RISK):
    return TradeCandidate(
        parsed_signal_id=f"parsed-{source}",
        source=source,
        status=status,
        symbol="EUR_USD",
        action=action,
        stop_loss="1.0950",
        take_profits=["1.1100"],
    )


def signal(source="alpha", action="buy", source_type=SignalSourceType.TELEGRAM, weight=1.0):
    return StrategySignal(
        source_type=source_type,
        source_name=source,
        candidate=candidate(source=source, action=action),
        weight=weight,
    )


def engine(tmp_path):
    return StrategyFusionEngine(
        ledger=EventLedger(path=str(tmp_path / "fusion.json")),
        minimum_weight=1.0,
    )


def test_fusion_agreement(tmp_path):
    decision = engine(tmp_path).fuse([
        signal("telegram", "buy", SignalSourceType.TELEGRAM),
        signal("manual", "buy", SignalSourceType.MANUAL),
    ])

    assert decision.approved is True
    assert decision.candidate.action == "buy"
    assert len(decision.contributions) == 2


def test_fusion_disagreement_rejected(tmp_path):
    decision = engine(tmp_path).fuse([
        signal("telegram", "buy"),
        signal("webhook", "sell", SignalSourceType.WEBHOOK),
    ])

    assert decision.approved is False
    assert decision.reason == "Strategy sources disagree"


def test_invalid_source_ignored(tmp_path):
    decision = engine(tmp_path).fuse([
        StrategySignal(
            source_type=SignalSourceType.WEBHOOK,
            source_name="bad",
            candidate=candidate(status=TradeCandidateStatus.OBSERVE_ONLY),
        )
    ])

    assert decision.approved is False
    assert decision.reason == "No valid strategy signals"


def test_ledger_events_emitted(tmp_path):
    fusion = engine(tmp_path)

    fusion.fuse([signal("telegram", "buy")])

    event_types = [event["payload"]["event_type"] for event in fusion.ledger.all_events()]

    assert StrategyFusionEventType.STRATEGY_SIGNAL_RECEIVED.value in event_types
    assert StrategyFusionEventType.STRATEGY_FUSION_APPROVED.value in event_types


def test_strategy_fusion_has_no_execution_or_broker_imports():
    source = inspect.getsource(fusion_module)

    for forbidden in ["TradeExecutor", "BrokerFactory", "OandaBroker", "PaperBroker"]:
        assert forbidden not in source
