from contracts.execution_request import ExecutionRequest
from contracts.execution_result import ContractExecutionStatus, ExecutionResult
from contracts.parsed_signal import ParsedSignal, ParsedSignalStatus
from contracts.raw_message import RawMessage
from contracts.risk_decision import RiskDecision, RiskDecisionStatus
from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus
from decision.decision_engine import DecisionEngine
from decision.ml_model import MLModel, ModelDecisionContext
from events.models import DecisionEvent
from execution.brokers.base import BaseBroker
from execution.execution_service import ExecutionService
from orchestration.pipeline import _NoopLedger
from orchestration.pipeline import Pipeline


class FakeLedger:
    def __init__(self):
        self.events = []

    def append(self, event: DecisionEvent):
        self.events.append(event.to_dict())
        return self.events[-1]

    def all_events(self):
        return list(self.events)


class FakeParser:
    def __init__(self):
        self.called = False

    def parse_raw_message(self, raw_message):
        self.called = True
        return ParsedSignal(
            raw_message_id=raw_message.id,
            source=raw_message.source,
            status=ParsedSignalStatus.VALID_SIGNAL,
            symbol="EUR_USD",
            action="buy",
            entry_price="1.1000",
            stop_loss="1.0950",
            take_profits=["1.1100"],
        )


class FakeBroker(BaseBroker):
    env = "paper"
    account_id = "fake-account"

    def get_price(self, symbol: str):
        return {"bid": 1.0999, "ask": 1.1001, "mid": 1.1, "tradeable": True}

    def place_order(self, symbol, units, entry_price=None, take_profit=None, stop_loss=None):
        return {"orderFillTransaction": {"tradeOpened": {"tradeID": "fake-trade"}}}

    def get_open_trades(self, symbol: str | None = None):
        return []

    def get_trade(self, trade_id: str):
        return {"id": trade_id, "state": "OPEN"}

    def close_trade(self, trade_id: str):
        return {"orderFillTransaction": {"tradesClosed": [{"tradeID": trade_id}]}}

    def close_open_trades(self, symbol: str | None = None):
        return []


class FakeBrokerExecutor:
    def __init__(self, broker):
        self.broker = broker
        self.called = False

    def execute_request(self, request):
        self.called = True
        self.broker.place_order(request.symbol, request.units)
        return ExecutionResult(
            execution_request_id=request.id,
            status=ContractExecutionStatus.FILLED,
            broker=request.broker,
            account_id=request.account_id or self.broker.account_id,
            symbol=request.symbol,
            action=request.action,
            requested_units=request.units,
            broker_trade_id="fake-trade",
        )


def raw_message():
    return RawMessage(
        source="replaceability",
        message_id="1",
        posted_at="2026-01-01T00:00:00+00:00",
        received_at="2026-01-01T00:00:01+00:00",
        raw_text="anything",
    )


def test_parser_can_be_replaced_in_pipeline():
    fake_parser = FakeParser()
    ledger = FakeLedger()

    result = Pipeline(parser=fake_parser, ledger=ledger).run(raw_message())

    assert fake_parser.called is True
    assert isinstance(result.parsed_signal, ParsedSignal)
    assert isinstance(result.trade_candidate, TradeCandidate)


def test_event_store_can_be_replaced_with_fake_ledger():
    ledger = FakeLedger()

    Pipeline(parser=FakeParser(), ledger=ledger).run(raw_message())

    assert [event["stage"] for event in ledger.all_events()] == ["parsing", "decision"]


def test_broker_can_be_replaced_behind_execution_boundary():
    broker = FakeBroker()
    executor = FakeBrokerExecutor(broker)
    request = ExecutionRequest(
        capital_allocation_id="capital-1",
        source="replaceability",
        broker="paper",
        account_id="fake-account",
        symbol="EUR_USD",
        action="buy",
        units=100,
    )

    result = ExecutionService(executor=executor).execute(request)

    assert executor.called is True
    assert result.status == ContractExecutionStatus.FILLED
    assert result.broker_trade_id == "fake-trade"


def test_ml_advisory_can_be_replaced_by_prediction_contract():
    signal = ParsedSignal(
        raw_message_id="raw-1",
        source="replaceability",
        status=ParsedSignalStatus.VALID_SIGNAL,
        symbol="EUR_USD",
        action="buy",
        entry_price="1.1000",
        stop_loss="1.0950",
        take_profits=["1.1100"],
    )
    prediction = MLModel(ledger=_NoopLedger()).score(signal, ModelDecisionContext(source_score=100))

    outcome = DecisionEngine(ledger=_NoopLedger()).evaluate_decision(signal, ml_prediction=prediction)

    assert outcome.candidate.status == TradeCandidateStatus.APPROVED_FOR_RISK


def test_fake_risk_decision_provider_can_feed_capital_boundary():
    candidate = TradeCandidate(
        parsed_signal_id="parsed-1",
        source="replaceability",
        status=TradeCandidateStatus.APPROVED_FOR_RISK,
        symbol="EUR_USD",
        action="buy",
        entry_price="1.1000",
        stop_loss="1.0950",
        take_profits=["1.1100"],
    )
    decision = RiskDecision(
        trade_candidate_id=candidate.id,
        status=RiskDecisionStatus.APPROVED,
    )

    assert decision.trade_candidate_id == candidate.id
