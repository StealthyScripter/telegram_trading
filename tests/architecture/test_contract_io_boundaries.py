import pytest

from capital.allocator import CapitalAllocator
from capital.execution_request_factory import ExecutionRequestFactory
from capital.models import AccountCapitalState
from contracts.capital_allocation import CapitalAllocation
from contracts.execution_request import ExecutionRequest
from contracts.execution_result import ContractExecutionStatus, ExecutionResult
from contracts.parsed_signal import ParsedSignal, ParsedSignalStatus
from contracts.raw_message import RawMessage
from contracts.risk_decision import RiskDecision, RiskDecisionStatus
from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus
from decision.decision_engine import DecisionEngine, DecisionOutcome
from decision.ensemble import EnsembleDecision, EnsembleDecisionEngine
from decision.ml_model import MLModel, SignalQualityPrediction
from events.ledger import EventLedger
from events.models import DecisionEvent
from execution.execution_service import ExecutionService
from learning.recommendation_engine import LearningRecommendation, RecommendationEngine
from learning.source_evaluator import SourceEvaluation, SourceHealth
from orchestration.pipeline import _NoopLedger
from parsing.parser import SignalParser
from risk.portfolio import PortfolioState
from risk.risk_engine import RiskEngine


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


def risk_decision(candidate_id: str):
    return RiskDecision(
        trade_candidate_id=candidate_id,
        status=RiskDecisionStatus.APPROVED,
    )


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


def test_parser_accepts_raw_message_and_returns_parsed_signal():
    result = SignalParser().parse_raw_message(raw_message())

    assert isinstance(result, ParsedSignal)


def test_candidate_creation_accepts_parsed_signal_and_returns_trade_candidate():
    result = DecisionEngine(ledger=_NoopLedger()).evaluate(parsed_signal())

    assert isinstance(result, TradeCandidate)


def test_decision_engine_returns_decision_outcome():
    outcome = DecisionEngine(ledger=_NoopLedger()).evaluate_decision(parsed_signal())

    assert isinstance(outcome, DecisionOutcome)
    assert isinstance(outcome.candidate, TradeCandidate)


def test_ensemble_accepts_trade_candidates_and_returns_decision():
    result = EnsembleDecisionEngine(ledger=_NoopLedger()).evaluate([trade_candidate()])

    assert isinstance(result, EnsembleDecision)


def test_ml_advisory_accepts_contract_and_does_not_return_execution_request():
    prediction = MLModel(ledger=_NoopLedger()).score(parsed_signal())

    assert isinstance(prediction, SignalQualityPrediction)
    assert not isinstance(prediction, ExecutionRequest)


def test_risk_accepts_trade_candidate_and_returns_risk_decision():
    result = RiskEngine(ledger=_NoopLedger()).evaluate(
        trade_candidate(),
        PortfolioState(account_id="paper-1", broker="paper", equity=10000),
    )

    assert isinstance(result, RiskDecision)


def test_capital_accepts_risk_decision_and_returns_capital_allocation():
    candidate = trade_candidate()
    result = CapitalAllocator(ledger=_NoopLedger()).allocate(
        candidate=candidate,
        risk_decision=risk_decision(candidate.id),
        account_state=AccountCapitalState(
            account_id="paper-1",
            broker="paper",
            balance=10000,
            equity=10000,
            available_margin=10000,
        ),
    )

    assert isinstance(result, CapitalAllocation)


def test_execution_request_factory_returns_execution_request():
    candidate = trade_candidate()
    risk = risk_decision(candidate.id)
    allocation = CapitalAllocator(ledger=_NoopLedger()).allocate(
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

    result = ExecutionRequestFactory().create(allocation, candidate, risk)

    assert isinstance(result, ExecutionRequest)


def test_execution_service_accepts_execution_request_and_returns_execution_result():
    request = ExecutionRequest(
        capital_allocation_id="capital-1",
        source="architecture",
        broker="paper",
        account_id="paper-1",
        symbol="EUR_USD",
        action="buy",
        units=100,
    )

    result = ExecutionService(executor=FakeExecutor()).execute(request)

    assert isinstance(result, ExecutionResult)


def test_learning_returns_recommendation_not_execution_request():
    result = RecommendationEngine(ledger=_NoopLedger()).recommend(
        SourceEvaluation("alpha", SourceHealth.STABLE, "stable")
    )

    assert isinstance(result, LearningRecommendation)
    assert not isinstance(result, ExecutionRequest)


def test_event_ledger_accepts_event_object_and_returns_event_stream(tmp_path):
    ledger = EventLedger(path=str(tmp_path / "events.json"))

    ledger.append(DecisionEvent(stage="architecture", input_id="in", output_id="out"))

    assert ledger.all_events()[0]["stage"] == "architecture"


@pytest.mark.parametrize("bad_input", [raw_message(), parsed_signal(), {}])
def test_execution_rejects_non_execution_request(bad_input):
    with pytest.raises(TypeError):
        ExecutionService(executor=FakeExecutor()).execute(bad_input)


def test_parser_rejects_execution_request():
    with pytest.raises(Exception):
        SignalParser().parse_raw_message(
            ExecutionRequest(
                capital_allocation_id="capital-1",
                source="architecture",
                broker="paper",
                symbol="EUR_USD",
                action="buy",
                units=1,
            )
        )


def test_risk_rejects_raw_message():
    with pytest.raises(Exception):
        RiskEngine(ledger=_NoopLedger()).evaluate(raw_message())


def test_capital_rejects_raw_message():
    with pytest.raises(Exception):
        CapitalAllocator(ledger=_NoopLedger()).allocate(
            candidate=trade_candidate(),
            risk_decision=raw_message(),
            account_state=AccountCapitalState(
                account_id="paper-1",
                broker="paper",
                balance=10000,
                equity=10000,
                available_margin=10000,
            ),
        )
