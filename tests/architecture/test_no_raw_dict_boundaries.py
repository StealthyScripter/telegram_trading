import pytest

from capital.allocator import CapitalAllocator
from capital.models import AccountCapitalState
from decision.decision_engine import DecisionEngine
from events.ledger import EventLedger
from execution.execution_service import ExecutionService
from learning.recommendation_engine import RecommendationEngine
from orchestration.pipeline import _NoopLedger
from parsing.parser import SignalParser
from risk.risk_engine import RiskEngine


class FakeExecutor:
    def execute_request(self, request):
        raise AssertionError("core execution should reject dict before executor")


def test_parser_rejects_dict_pretending_to_be_raw_message():
    with pytest.raises(Exception):
        SignalParser().parse_raw_message({"raw_text": "BUY EURUSD"})


def test_decision_rejects_dict_pretending_to_be_parsed_signal():
    with pytest.raises(Exception):
        DecisionEngine(ledger=_NoopLedger()).evaluate({"status": "VALID_SIGNAL"})


def test_risk_rejects_dict_pretending_to_be_candidate():
    with pytest.raises(Exception):
        RiskEngine(ledger=_NoopLedger()).evaluate({"status": "APPROVED_FOR_RISK"})


def test_capital_rejects_dict_pretending_to_be_risk_decision():
    with pytest.raises(Exception):
        CapitalAllocator(ledger=_NoopLedger()).allocate(
            candidate={"id": "candidate"},
            risk_decision={"status": "APPROVED"},
            account_state=AccountCapitalState(
                account_id="paper-1",
                broker="paper",
                balance=10000,
                equity=10000,
                available_margin=10000,
            ),
        )


def test_execution_service_rejects_dict_pretending_to_be_execution_request():
    with pytest.raises(TypeError):
        ExecutionService(executor=FakeExecutor()).execute({"symbol": "EUR_USD"})


def test_event_ledger_rejects_dict_pretending_to_be_event(tmp_path):
    with pytest.raises(Exception):
        EventLedger(path=str(tmp_path / "events.json")).append({"stage": "decision"})


def test_learning_recommendation_rejects_dict_pretending_to_be_evaluation():
    with pytest.raises(Exception):
        RecommendationEngine(ledger=_NoopLedger()).recommend({"source": "alpha"})
