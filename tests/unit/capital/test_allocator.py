import inspect
import json

import pytest

from capital import allocator as allocator_module
from capital.allocator import CapitalAllocator, CapitalEventType
from capital.models import (
    AccountCapitalState,
    AccountMode,
    AllocationConfig,
    ChannelWeightRule,
)
from contracts.risk_decision import RiskDecision, RiskDecisionStatus
from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus
from decision.channel_intelligence import (
    ApprovalState,
    ChannelGrade,
    DecisionContext,
    ManualOverride,
    PromotionAction,
    PromotionDecision,
)
from events.ledger import EventLedger


def candidate(**overrides):
    data = {
        "parsed_signal_id": "parsed-1",
        "source": "telegram_alpha",
        "status": TradeCandidateStatus.APPROVED_FOR_RISK,
        "symbol": "EUR_USD",
        "action": "buy",
        "entry_price": "1.1000",
        "stop_loss": "1.0950",
        "take_profits": ["1.1100"],
        "strategy_account": "scalping",
    }
    data.update(overrides)
    return TradeCandidate(**data)


def risk_decision(trade_candidate_id, **overrides):
    data = {
        "trade_candidate_id": trade_candidate_id,
        "status": RiskDecisionStatus.APPROVED,
    }
    data.update(overrides)
    return RiskDecision(**data)


def account_state(mode=AccountMode.PAPER):
    return AccountCapitalState(
        account_id="acct-1",
        broker="oanda",
        balance=10000,
        equity=10000,
        available_margin=9000,
        currency="USD",
        mode=mode,
    )


def config(**overrides):
    data = {
        "base_risk_percent": 0.01,
        "min_risk_percent": 0.001,
        "max_risk_percent": 0.02,
        "paper_multiplier": 1.0,
        "live_multiplier": 1.0,
        "min_units": 1,
        "max_units": 50000,
        "enable_channel_weighting": False,
    }
    data.update(overrides)
    return AllocationConfig(**data)


def channel_context(score):
    return DecisionContext(
        source_name="telegram_alpha",
        channel_score=score,
        grade=ChannelGrade.LIVE,
        approval_state=ApprovalState.AUTOMATIC,
        manual_override=ManualOverride.NONE,
        paper_enabled=True,
        live_enabled=True,
        promotion_decision=PromotionDecision(
            action=PromotionAction.PROMOTE,
            grade=ChannelGrade.LIVE,
            reason="ok",
        ),
        approval_reason="ok",
    )


def allocator(tmp_path, allocation_config=None):
    return CapitalAllocator(
        config=allocation_config or config(),
        ledger=EventLedger(path=str(tmp_path / "capital_ledger.json")),
    )


def test_approved_allocation_sizes_units(tmp_path):
    trade = candidate()
    risk = risk_decision(trade.id)

    allocation = allocator(tmp_path).allocate(
        candidate=trade,
        risk_decision=risk,
        account_state=account_state(),
    )

    assert allocation.risk_decision_id == risk.id
    assert allocation.units == 20000
    assert allocation.risk_amount == 100
    assert allocation.risk_percent == 0.01
    assert allocation.account_id == "acct-1"
    assert allocation.broker == "oanda"


def test_rejected_risk_decision_rejects_allocation(tmp_path):
    trade = candidate()
    risk = risk_decision(
        trade.id,
        status=RiskDecisionStatus.REJECTED,
        reason="risk rejected",
    )

    with pytest.raises(ValueError, match="risk rejected"):
        allocator(tmp_path).allocate(
            candidate=trade,
            risk_decision=risk,
            account_state=account_state(),
        )


def test_missing_stop_loss_rejected(tmp_path):
    trade = candidate(stop_loss=None)
    risk = risk_decision(trade.id)

    with pytest.raises(ValueError, match="Missing stop loss"):
        allocator(tmp_path).allocate(trade, risk, account_state())


def test_missing_entry_rejected(tmp_path):
    trade = candidate(entry_price=None)
    risk = risk_decision(trade.id)

    with pytest.raises(ValueError, match="Missing entry price"):
        allocator(tmp_path).allocate(trade, risk, account_state())


def test_expected_entry_price_used_when_candidate_entry_missing(tmp_path):
    trade = candidate(entry_price=None)
    risk = risk_decision(trade.id)

    allocation = allocator(tmp_path).allocate(
        trade,
        risk,
        account_state(),
        expected_entry_price="1.1000",
    )

    assert allocation.units == 20000


def test_current_price_used_when_entry_and_expected_missing(tmp_path):
    trade = candidate(entry_price=None)
    risk = risk_decision(trade.id)

    allocation = allocator(tmp_path).allocate(
        trade,
        risk,
        account_state(),
        current_price="1.1000",
    )

    assert allocation.units == 20000


def test_zero_stop_distance_rejected(tmp_path):
    trade = candidate(stop_loss="1.1000")
    risk = risk_decision(trade.id)

    with pytest.raises(ValueError, match="Stop distance"):
        allocator(tmp_path).allocate(trade, risk, account_state())


def test_negative_stop_loss_rejected(tmp_path):
    trade = candidate(stop_loss="-1.0950")
    risk = risk_decision(trade.id)

    with pytest.raises(ValueError, match="positive"):
        allocator(tmp_path).allocate(trade, risk, account_state())


def test_minimum_units_clamp(tmp_path):
    trade = candidate(stop_loss="0.1000")
    risk = risk_decision(trade.id)
    low_config = config(base_risk_percent=0.001, min_units=10, max_units=50000)

    allocation = allocator(tmp_path, low_config).allocate(
        trade,
        risk,
        account_state(),
    )

    assert allocation.calculated_units == 10
    assert allocation.units == 10


def test_maximum_units_clamp(tmp_path):
    trade = candidate(stop_loss="1.0999")
    risk = risk_decision(trade.id)
    capped_config = config(max_units=1000)

    allocation = allocator(tmp_path, capped_config).allocate(
        trade,
        risk,
        account_state(),
    )

    assert allocation.calculated_units > allocation.units
    assert allocation.units == 1000


def test_channel_weighting_reduces_units(tmp_path):
    trade = candidate()
    risk = risk_decision(trade.id)
    weighted_config = config(
        enable_channel_weighting=True,
        minimum_channel_score=50,
        channel_weight_rules=(
            ChannelWeightRule(minimum_score=90, multiplier=1.0),
            ChannelWeightRule(minimum_score=70, multiplier=0.5),
            ChannelWeightRule(minimum_score=0, multiplier=0.25),
        ),
    )

    allocation = allocator(tmp_path, weighted_config).allocate(
        trade,
        risk,
        account_state(),
        decision_context=channel_context(75),
    )

    assert allocation.risk_percent == 0.005
    assert allocation.units == 10000


def test_channel_score_below_minimum_rejected(tmp_path):
    trade = candidate()
    risk = risk_decision(trade.id)
    weighted_config = config(enable_channel_weighting=True, minimum_channel_score=60)

    with pytest.raises(ValueError, match="Risk percent"):
        allocator(tmp_path, weighted_config).allocate(
            trade,
            risk,
            account_state(),
            decision_context=channel_context(50),
        )


def test_paper_and_live_multipliers(tmp_path):
    trade = candidate()
    risk = risk_decision(trade.id)
    mode_config = config(paper_multiplier=0.5, live_multiplier=1.5)
    capital_allocator = allocator(tmp_path, mode_config)

    paper = capital_allocator.allocate(trade, risk, account_state(AccountMode.PAPER))
    live = capital_allocator.allocate(trade, risk, account_state(AccountMode.LIVE))

    assert paper.risk_percent == 0.005
    assert live.risk_percent == 0.015
    assert live.units == paper.units * 3


def test_ledger_emits_created_and_clamped_events(tmp_path):
    trade = candidate(stop_loss="1.0999")
    risk = risk_decision(trade.id)
    capital_allocator = allocator(tmp_path, config(max_units=1000))

    capital_allocator.allocate(trade, risk, account_state())

    events = capital_allocator.ledger.all_events()
    event_types = [event["payload"]["event_type"] for event in events]

    assert CapitalEventType.CAPITAL_ALLOCATION_CLAMPED.value in event_types
    assert CapitalEventType.CAPITAL_ALLOCATION_CREATED.value in event_types
    created = events[-1]["payload"]
    assert created["trade_candidate_id"] == trade.id
    assert created["risk_decision_id"] == risk.id
    assert created["account_id"] == "acct-1"


def test_rejected_allocation_emits_ledger_event(tmp_path):
    trade = candidate(stop_loss=None)
    risk = risk_decision(trade.id)
    capital_allocator = allocator(tmp_path)

    with pytest.raises(ValueError):
        capital_allocator.allocate(trade, risk, account_state())

    event = capital_allocator.ledger.all_events()[0]

    assert event["payload"]["event_type"] == CapitalEventType.CAPITAL_ALLOCATION_REJECTED.value


def test_configuration_loading(tmp_path):
    path = tmp_path / "allocation_config.json"
    path.write_text(
        json.dumps(
            {
                "base_risk_percent": 0.02,
                "min_units": 5,
                "channel_weight_rules": [
                    {"minimum_score": 80, "multiplier": 0.75},
                ],
            }
        ),
        encoding="utf-8",
    )

    loaded = AllocationConfig.from_path(str(path))

    assert loaded.base_risk_percent == 0.02
    assert loaded.min_units == 5
    assert loaded.channel_weight_rules[0].minimum_score == 80


def test_legacy_explicit_units_path_remains_compatible(tmp_path):
    trade = candidate()
    risk = risk_decision(trade.id)

    allocation = allocator(tmp_path).allocate(
        candidate=trade,
        risk_decision=risk,
        units=123,
        broker="oanda",
        account_id="acct-legacy",
        strategy_account="scalping",
    )

    assert allocation.units == 123
    assert allocation.account_id == "acct-legacy"
    assert allocation.reason == "Capital scaffold allocation"


def test_capital_allocator_has_no_execution_or_broker_imports():
    source = inspect.getsource(allocator_module)

    forbidden = [
        "TradeExecutor",
        "CloseExecutor",
        "BrokerFactory",
        "OandaBroker",
        "PaperBroker",
        "Telegram",
        "SignalParser",
        "ML",
    ]

    for name in forbidden:
        assert name not in source
