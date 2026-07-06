import pytest
from dataclasses import FrozenInstanceError

from contracts.capital_allocation import CapitalAllocation
from contracts.execution_request import ExecutionMode, ExecutionRequest
from contracts.execution_result import (
    ContractExecutionResult,
    ContractExecutionStatus,
)
from contracts.parsed_signal import ParsedSignal, ParsedSignalStatus
from contracts.raw_message import RawMessage
from contracts.risk_decision import RiskDecision, RiskDecisionStatus
from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus


def test_raw_message_contract():
    message = RawMessage(
        source="telegram_channel",
        message_id="123",
        raw_text="BUY EURUSD SL 1.1300 TP 1.1400",
        posted_at="2026-01-01T10:00:00+00:00",
        received_at="2026-01-01T10:00:01+00:00",
    )

    assert message.source == "telegram_channel"
    assert message.to_dict()["raw_text"] == "BUY EURUSD SL 1.1300 TP 1.1400"


def test_contracts_are_immutable():
    message = RawMessage(
        source="telegram_test",
        message_id="1",
        raw_text="BUY EURUSD",
        posted_at="2026-01-01T10:00:00+00:00",
        received_at="2026-01-01T10:00:01+00:00",
    )

    with pytest.raises(FrozenInstanceError):
        message.source = "changed"


def test_raw_message_rejects_empty_text():
    with pytest.raises(ValueError, match="raw_text"):
        RawMessage(
            source="telegram_channel",
            message_id="123",
            raw_text=" ",
        )


def test_valid_parsed_signal_contract():
    signal = ParsedSignal(
        raw_message_id="raw-1",
        source="telegram_channel",
        status=ParsedSignalStatus.VALID_SIGNAL,
        symbol="EUR_USD",
        action="buy",
        stop_loss="1.1300",
        take_profits=["1.1400"],
    )

    assert signal.status == ParsedSignalStatus.VALID_SIGNAL


def test_valid_parsed_signal_requires_required_fields():
    with pytest.raises(ValueError, match="VALID_SIGNAL missing"):
        ParsedSignal(
            raw_message_id="raw-1",
            status=ParsedSignalStatus.VALID_SIGNAL,
            symbol="EUR_USD",
            action="buy",
        )


def test_trade_candidate_contract():
    candidate = TradeCandidate(
        parsed_signal_id="parsed-1",
        source="telegram_channel",
        status=TradeCandidateStatus.APPROVED_FOR_RISK,
        symbol="EUR_USD",
        action="buy",
        confidence=0.8,
    )

    assert candidate.confidence == 0.8


def test_trade_candidate_rejects_invalid_confidence():
    with pytest.raises(ValueError, match="confidence"):
        TradeCandidate(
            parsed_signal_id="parsed-1",
            confidence=1.5,
        )


def test_risk_decision_contract():
    decision = RiskDecision(
        trade_candidate_id="candidate-1",
        status=RiskDecisionStatus.APPROVED,
        max_risk_percent=1.0,
    )

    assert decision.status == RiskDecisionStatus.APPROVED


def test_rejected_risk_decision_requires_reason():
    with pytest.raises(ValueError, match="reason"):
        RiskDecision(
            trade_candidate_id="candidate-1",
            status=RiskDecisionStatus.REJECTED,
        )


def test_capital_allocation_contract():
    allocation = CapitalAllocation(
        risk_decision_id="risk-1",
        symbol="EUR_USD",
        action="buy",
        units=1000,
        broker="oanda",
        strategy_account="scalping",
    )

    assert allocation.units == 1000


def test_execution_request_contract():
    request = ExecutionRequest(
        capital_allocation_id="capital-1",
        source="telegram_channel",
        broker="oanda",
        strategy_account="scalping",
        symbol="EUR_USD",
        action="buy",
        units=1000,
        take_profit="1.1400",
        stop_loss="1.1300",
        mode=ExecutionMode.PAPER,
    )

    assert request.mode == ExecutionMode.PAPER


def test_execution_request_rejects_invalid_action():
    with pytest.raises(ValueError, match="action"):
        ExecutionRequest(
            capital_allocation_id="capital-1",
            symbol="EUR_USD",
            action="hold",
            units=1000,
        )


def test_execution_result_contract():
    result = ContractExecutionResult(
        execution_request_id="request-1",
        status=ContractExecutionStatus.FILLED,
        broker="oanda",
        account_id="acct-1",
        symbol="EUR_USD",
        action="buy",
        requested_units=1000,
        broker_trade_id="123",
    )

    assert result.status == ContractExecutionStatus.FILLED
