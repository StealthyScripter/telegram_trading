from dataclasses import FrozenInstanceError

import pytest

from capital.execution_request_factory import ExecutionRequestFactory
from capital.models import AccountCapitalState
from capital.allocator import CapitalAllocator
from contracts.execution_request import ExecutionRequest
from contracts.execution_result import ContractExecutionStatus, ExecutionResult
from contracts.raw_message import RawMessage
from contracts.risk_decision import RiskDecision, RiskDecisionStatus
from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus
from execution.execution_service import ExecutionService
from events.ledger import EventLedger
from parsing.parser import SignalParser


def test_contract_objects_are_immutable_at_pipeline_boundary():
    message = RawMessage(
        source="contract_test",
        message_id="1",
        posted_at="2026-01-01T10:00:00+00:00",
        received_at="2026-01-01T10:00:01+00:00",
        raw_text="BUY EURUSD SL 1.0950 TP 1.1100",
    )

    with pytest.raises(FrozenInstanceError):
        message.raw_text = "changed"


def test_parser_accepts_raw_message_contract_and_returns_parsed_signal_contract():
    message = RawMessage(
        source="contract_test",
        message_id="1",
        posted_at="2026-01-01T10:00:00+00:00",
        received_at="2026-01-01T10:00:01+00:00",
        raw_text="BUY EURUSD SL 1.0950 TP 1.1100",
    )

    parsed = SignalParser().parse_raw_message(message)

    assert parsed.raw_message_id == message.id
    assert parsed.id
    assert parsed.to_dict()["symbol"] == "EUR_USD"


def test_capital_allocation_to_execution_request_uses_contracts_only(tmp_path):
    candidate = TradeCandidate(
        parsed_signal_id="parsed-1",
        source="contract_test",
        status=TradeCandidateStatus.APPROVED_FOR_RISK,
        symbol="EUR_USD",
        action="buy",
        entry_price="1.1000",
        stop_loss="1.0950",
        take_profits=["1.1100"],
    )
    risk = RiskDecision(
        trade_candidate_id=candidate.id,
        status=RiskDecisionStatus.APPROVED,
    )
    allocation = CapitalAllocator(
        ledger=EventLedger(path=str(tmp_path / "decision_events.json")),
    ).allocate(
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

    request = ExecutionRequestFactory().create(allocation, candidate, risk)

    assert isinstance(request, ExecutionRequest)
    assert request.capital_allocation_id == allocation.id


def test_execution_service_accepts_execution_request_and_returns_execution_result():
    class FakeExecutor:
        def execute_request(self, request):
            assert isinstance(request, ExecutionRequest)
            return ExecutionResult(
                execution_request_id=request.id,
                status=ContractExecutionStatus.FILLED,
                broker=request.broker,
                account_id=request.account_id or "paper-1",
                symbol=request.symbol,
                action=request.action,
                requested_units=request.units,
            )

    request = ExecutionRequest(
        capital_allocation_id="capital-1",
        source="contract_test",
        broker="paper",
        account_id="paper-1",
        symbol="EUR_USD",
        action="buy",
        units=1,
    )

    result = ExecutionService(executor=FakeExecutor()).execute(request)

    assert isinstance(result, ExecutionResult)
    assert result.execution_request_id == request.id
