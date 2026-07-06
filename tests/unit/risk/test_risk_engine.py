import inspect

from contracts.risk_decision import RiskDecisionStatus
from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus
from events.ledger import EventLedger
from risk import risk_engine as risk_module
from risk.exposure import OpenPosition
from risk.portfolio import PortfolioState, RiskPolicy
from risk.risk_engine import RiskEngine, RiskEventType


def candidate(**overrides):
    data = {
        "parsed_signal_id": "parsed-1",
        "source": "alpha",
        "status": TradeCandidateStatus.APPROVED_FOR_RISK,
        "symbol": "EUR_USD",
        "action": "buy",
        "stop_loss": "1.0950",
        "take_profits": ["1.1100"],
    }
    data.update(overrides)
    return TradeCandidate(**data)


def state(positions=None, **overrides):
    data = {
        "account_id": "acct-1",
        "broker": "oanda",
        "equity": 10000,
        "open_positions": positions or [],
        "daily_risk_used": 0,
        "weekly_risk_used": 0,
    }
    data.update(overrides)
    return PortfolioState(**data)


def engine(tmp_path, policy=None):
    return RiskEngine(
        policy=policy or RiskPolicy(),
        ledger=EventLedger(path=str(tmp_path / "risk_ledger.json")),
    )


def test_approved_risk(tmp_path):
    decision = engine(tmp_path).evaluate(candidate(), state())

    assert decision.status == RiskDecisionStatus.APPROVED
    assert decision.max_risk_percent == RiskPolicy().max_risk_percent


def test_rejected_daily_limit(tmp_path):
    decision = engine(
        tmp_path,
        RiskPolicy(max_daily_risk=100),
    ).evaluate(candidate(), state(daily_risk_used=100))

    assert decision.status == RiskDecisionStatus.REJECTED
    assert "daily" in decision.reason


def test_rejected_max_open_trades(tmp_path):
    positions = [
        OpenPosition("EUR_USD", "alpha", "oanda", "acct-1", 1000, 10),
    ]

    decision = engine(
        tmp_path,
        RiskPolicy(max_open_trades=1),
    ).evaluate(candidate(), state(positions))

    assert decision.status == RiskDecisionStatus.REJECTED
    assert "open trades" in decision.reason


def test_rejected_symbol_exposure(tmp_path):
    positions = [OpenPosition("EUR_USD", "beta", "oanda", "acct-1", 1000, 100)]

    decision = engine(
        tmp_path,
        RiskPolicy(max_symbol_exposure=100),
    ).evaluate(candidate(), state(positions))

    assert decision.status == RiskDecisionStatus.REJECTED
    assert "symbol" in decision.reason


def test_rejected_source_exposure(tmp_path):
    positions = [OpenPosition("GBP_USD", "alpha", "oanda", "acct-1", 1000, 100)]

    decision = engine(
        tmp_path,
        RiskPolicy(max_source_exposure=100),
    ).evaluate(candidate(), state(positions))

    assert decision.status == RiskDecisionStatus.REJECTED
    assert "source" in decision.reason


def test_rejected_account_exposure(tmp_path):
    positions = [OpenPosition("GBP_USD", "beta", "oanda", "acct-1", 1000, 100)]

    decision = engine(
        tmp_path,
        RiskPolicy(max_account_exposure=100),
    ).evaluate(candidate(), state(positions))

    assert decision.status == RiskDecisionStatus.REJECTED
    assert "account" in decision.reason


def test_rejected_broker_exposure(tmp_path):
    positions = [OpenPosition("GBP_USD", "beta", "oanda", "acct-1", 1000, 100)]

    decision = engine(
        tmp_path,
        RiskPolicy(max_broker_exposure=100),
    ).evaluate(candidate(), state(positions))

    assert decision.status == RiskDecisionStatus.REJECTED
    assert "broker" in decision.reason


def test_rejected_candidate_status(tmp_path):
    trade = candidate(status=TradeCandidateStatus.OBSERVE_ONLY, reason="observe only")

    decision = engine(tmp_path).evaluate(trade, state())

    assert decision.status == RiskDecisionStatus.REJECTED
    assert decision.reason == "observe only"


def test_ledger_events_emitted(tmp_path):
    risk = engine(tmp_path)

    risk.evaluate(candidate(), state())

    event_types = [event["payload"]["event_type"] for event in risk.ledger.all_events()]

    assert RiskEventType.EXPOSURE_UPDATED.value in event_types
    assert RiskEventType.RISK_APPROVED.value in event_types


def test_risk_engine_has_no_broker_execution_or_ingestion_imports():
    source = inspect.getsource(risk_module)

    for forbidden in [
        "TradeExecutor",
        "BrokerFactory",
        "OandaBroker",
        "Telegram",
        "SignalParser",
        "MLModel",
    ]:
        assert forbidden not in source
