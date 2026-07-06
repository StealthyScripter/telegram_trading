import pytest

from capital.execution_request_factory import ExecutionRequestFactory
from contracts.capital_allocation import CapitalAllocation
from contracts.execution_request import ExecutionMode
from contracts.risk_decision import RiskDecision, RiskDecisionStatus
from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus


def candidate():
    return TradeCandidate(
        parsed_signal_id="parsed-1",
        source="telegram_alpha",
        status=TradeCandidateStatus.APPROVED_FOR_RISK,
        symbol="EUR_USD",
        action="buy",
        entry_price="1.1000",
        stop_loss="1.0950",
        take_profits=["1.1100", "1.1200"],
        strategy_account="scalping",
    )


def risk_decision(candidate_id):
    return RiskDecision(
        trade_candidate_id=candidate_id,
        status=RiskDecisionStatus.APPROVED,
    )


def allocation(risk_id):
    return CapitalAllocation(
        risk_decision_id=risk_id,
        symbol="EUR_USD",
        action="buy",
        units=1000,
        broker="oanda",
        account_id="acct-1",
        strategy_account="scalping",
        risk_amount=50,
        risk_percent=0.005,
        calculated_units=1000,
        reason="approved",
    )


def test_execution_request_generation_preserves_fields():
    trade = candidate()
    risk = risk_decision(trade.id)
    capital = allocation(risk.id)

    request = ExecutionRequestFactory().create(
        allocation=capital,
        candidate=trade,
        risk_decision=risk,
        mode=ExecutionMode.PAPER,
    )

    assert request.capital_allocation_id == capital.id
    assert request.source == "telegram_alpha"
    assert request.broker == "oanda"
    assert request.account_id == "acct-1"
    assert request.strategy_account == "scalping"
    assert request.symbol == "EUR_USD"
    assert request.action == "buy"
    assert request.units == 1000
    assert request.entry_price == "1.1000"
    assert request.take_profit == "1.1100"
    assert request.stop_loss == "1.0950"
    assert request.mode == ExecutionMode.PAPER
    assert request.external_signal_id == "parsed-1"


def test_execution_request_factory_accepts_explicit_signal_id():
    trade = candidate()
    risk = risk_decision(trade.id)
    capital = allocation(risk.id)

    request = ExecutionRequestFactory().create(
        allocation=capital,
        candidate=trade,
        risk_decision=risk,
        external_signal_id="signal-override",
    )

    assert request.external_signal_id == "signal-override"


def test_execution_request_factory_rejects_mismatched_risk():
    trade = candidate()
    risk = risk_decision(trade.id)
    capital = allocation("other-risk")

    with pytest.raises(ValueError, match="RiskDecision"):
        ExecutionRequestFactory().create(capital, trade, risk)


def test_execution_request_factory_rejects_mismatched_candidate():
    trade = candidate()
    risk = RiskDecision(
        trade_candidate_id="other-candidate",
        status=RiskDecisionStatus.APPROVED,
    )
    capital = allocation(risk.id)

    with pytest.raises(ValueError, match="TradeCandidate"):
        ExecutionRequestFactory().create(capital, trade, risk)
