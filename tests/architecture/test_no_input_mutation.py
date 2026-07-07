import copy
from dataclasses import FrozenInstanceError

import pytest

from capital.allocator import CapitalAllocator
from capital.models import AccountCapitalState
from contracts.execution_request import ExecutionRequest
from contracts.execution_result import ContractExecutionStatus, ExecutionResult
from contracts.parsed_signal import ParsedSignal, ParsedSignalStatus
from contracts.raw_message import RawMessage
from contracts.risk_decision import RiskDecision, RiskDecisionStatus
from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus
from decision.decision_engine import DecisionEngine
from events.ledger import EventLedger
from events.models import DecisionEvent
from execution.execution_service import ExecutionService
from learning.recommendation_engine import RecommendationEngine
from learning.source_evaluator import SourceEvaluation, SourceHealth
from orchestration.pipeline import _NoopLedger
from parsing.parser import SignalParser
from risk.portfolio import PortfolioState
from risk.risk_engine import RiskEngine


class FakeExecutor:
    def execute_request(self, request):
        return ExecutionResult(
            execution_request_id=request.id,
            status=ContractExecutionStatus.FILLED,
            broker=request.broker,
            account_id=request.account_id or "paper-1",
            symbol=request.symbol,
            action=request.action,
            requested_units=request.units,
        )


def raw_message():
    return RawMessage(
        source="architecture",
        message_id="1",
        posted_at="2026-01-01T00:00:00+00:00",
        received_at="2026-01-01T00:00:01+00:00",
        raw_text="BUY EURUSD @ 1.1000 SL 1.0950 TP 1.1100",
    )


def parsed_signal():
    return ParsedSignal(
        raw_message_id="raw-1",
        source="architecture",
        status=ParsedSignalStatus.VALID_SIGNAL,
        symbol="EUR_USD",
        action="buy",
        entry_price="1.1000",
        stop_loss="1.0950",
        take_profits=["1.1100"],
    )


def trade_candidate():
    return TradeCandidate(
        parsed_signal_id="parsed-1",
        source="architecture",
        status=TradeCandidateStatus.APPROVED_FOR_RISK,
        symbol="EUR_USD",
        action="buy",
        entry_price="1.1000",
        stop_loss="1.0950",
        take_profits=["1.1100"],
    )


def assert_unchanged(obj, before):
    assert obj.to_dict() if hasattr(obj, "to_dict") else obj == before


def test_raw_message_not_mutated_by_parser():
    message = raw_message()
    before = message.to_dict()

    SignalParser().parse_raw_message(message)

    assert message.to_dict() == before


def test_parsed_signal_not_mutated_by_candidate_creation():
    signal = parsed_signal()
    before = signal.to_dict()

    DecisionEngine(ledger=_NoopLedger()).evaluate(signal)

    assert signal.to_dict() == before


def test_trade_candidate_not_mutated_by_decision_or_risk():
    candidate = trade_candidate()
    before = candidate.to_dict()

    DecisionEngine(ledger=_NoopLedger()).evaluate_decision(parsed_signal())
    RiskEngine(ledger=_NoopLedger()).evaluate(
        candidate,
        PortfolioState(account_id="paper-1", broker="paper", equity=10000),
    )

    assert candidate.to_dict() == before


def test_risk_decision_not_mutated_by_capital():
    candidate = trade_candidate()
    risk = RiskDecision(
        trade_candidate_id=candidate.id,
        status=RiskDecisionStatus.APPROVED,
    )
    before = risk.to_dict()

    CapitalAllocator(ledger=_NoopLedger()).allocate(
        candidate=candidate,
        risk_decision=risk,
        account_state=AccountCapitalState(
            account_id="paper-1",
            broker="paper",
            balance=10000,
            equity=10000,
            available_margin=10000,
        ),
    )

    assert risk.to_dict() == before


def test_execution_request_not_mutated_by_execution_service():
    request = ExecutionRequest(
        capital_allocation_id="capital-1",
        source="architecture",
        broker="paper",
        account_id="paper-1",
        symbol="EUR_USD",
        action="buy",
        units=100,
    )
    before = request.to_dict()

    ExecutionService(executor=FakeExecutor()).execute(request)

    assert request.to_dict() == before


def test_learning_input_not_mutated():
    evaluation = SourceEvaluation("alpha", SourceHealth.STABLE, "stable")
    before = copy.deepcopy(evaluation)

    RecommendationEngine(ledger=_NoopLedger()).recommend(evaluation)

    assert evaluation == before


def test_event_not_mutated_by_ledger(tmp_path):
    event = DecisionEvent(
        stage="architecture",
        input_id="in",
        output_id="out",
        payload={"nested": {"value": 1}},
    )
    before = event.to_dict()

    EventLedger(path=str(tmp_path / "events.json")).append(event)

    assert event.to_dict() == before


def test_contracts_are_immutable():
    message = raw_message()

    with pytest.raises(FrozenInstanceError):
        message.source = "mutated"
