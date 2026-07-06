from contracts.execution_result import ContractExecutionStatus, ExecutionResult
from contracts.raw_message import RawMessage
from contracts.risk_decision import RiskDecisionStatus
from contracts.trade_candidate import TradeCandidateStatus
from decision.ensemble import EnsembleDecisionEngine
from decision.ml_model import MLModel, ModelDecisionContext
from events.ledger import EventLedger
from execution.brokers.paper import PaperBroker
from orchestration.pipeline import Pipeline
from risk.portfolio import PortfolioState
from risk.risk_engine import RiskEngine
from capital.models import AccountCapitalState, AccountMode, AllocationConfig
from capital.allocator import CapitalAllocator
from capital.execution_request_factory import ExecutionRequestFactory
from contracts.execution_request import ExecutionMode
from learning.performance_memory import PerformanceMemory
from learning.source_evaluator import SourceEvaluator
from learning.recommendation_engine import RecommendationEngine


class PaperExecutionService:
    def __init__(self, broker: PaperBroker, ledger: EventLedger):
        self.broker = broker
        self.ledger = ledger

    def execute(self, request):
        response = self.broker.place_order(
            symbol=request.symbol,
            units=request.units if request.action == "buy" else -request.units,
            entry_price=request.entry_price,
            take_profit=request.take_profit,
            stop_loss=request.stop_loss,
        )
        fill = response["orderFillTransaction"]
        opened = fill["tradeOpened"]
        return ExecutionResult(
            execution_request_id=request.id,
            status=ContractExecutionStatus.FILLED,
            broker="paper",
            account_id=request.account_id or self.broker.account_id,
            symbol=request.symbol,
            action=request.action,
            requested_units=request.units,
            broker_trade_id=opened["tradeID"],
            broker_order_id=fill["orderID"],
            fill_price=opened["price"],
            reason=fill["reason"],
            raw_response=response,
        )


def raw_message(source="e2e_alpha", text="BUY EURUSD @ 1.1000 SL 1.0950 TP 1.1100"):
    return RawMessage(
        source=source,
        message_id=f"{source}-1",
        posted_at="2026-01-01T10:00:00+00:00",
        received_at="2026-01-01T10:00:01+00:00",
        raw_text=text,
    )


def run_full_paper_flow(tmp_path, source="e2e_alpha"):
    ledger = EventLedger(path=str(tmp_path / "decision_ledger.json"))
    pipeline = Pipeline(ledger=ledger)
    pipeline_result = pipeline.run(raw_message(source=source))

    ensemble = EnsembleDecisionEngine(ledger=ledger)
    ensemble_decision = ensemble.evaluate([pipeline_result.trade_candidate])

    ml_model = MLModel(ledger=ledger)
    ml_prediction = ml_model.score(
        ensemble_decision.candidate,
        ModelDecisionContext(source_score=90, minimum_score=0.5),
    )

    risk_engine = RiskEngine(ledger=ledger)
    risk_decision = risk_engine.evaluate(
        ensemble_decision.candidate,
        PortfolioState(account_id="paper-1", broker="paper", equity=10000),
    )

    allocator = CapitalAllocator(
        config=AllocationConfig(
            base_risk_percent=0.001,
            min_risk_percent=0.001,
            max_risk_percent=0.001,
            min_units=1,
            max_units=1000,
            enable_channel_weighting=False,
        ),
        ledger=ledger,
    )
    allocation = allocator.allocate(
        candidate=ensemble_decision.candidate,
        risk_decision=risk_decision,
        account_state=AccountCapitalState(
            account_id="paper-1",
            broker="paper",
            balance=10000,
            equity=10000,
            available_margin=10000,
            mode=AccountMode.PAPER,
        ),
    )

    execution_request = ExecutionRequestFactory().create(
        allocation=allocation,
        candidate=ensemble_decision.candidate,
        risk_decision=risk_decision,
        mode=ExecutionMode.PAPER,
    )
    paper_execution = PaperExecutionService(
        broker=PaperBroker(account_id="paper-1", price=1.1000),
        ledger=ledger,
    )
    execution_pipeline = Pipeline(ledger=ledger, execution_service=paper_execution)
    execution_result = execution_pipeline.run(raw_message(source=source), execution_request).execution_result

    learning_events = [
        {"payload": {"source": source, "realized_r": 1.0}},
        {"payload": {"source": source, "realized_r": 0.5}},
    ]
    memory = PerformanceMemory().build(learning_events)
    evaluation = SourceEvaluator().evaluate(memory[source])
    recommendation_engine = RecommendationEngine(ledger=ledger)
    recommendation = recommendation_engine.recommend(evaluation)

    return {
        "ledger": ledger,
        "raw_message": pipeline_result.raw_message,
        "parsed_signal": pipeline_result.parsed_signal,
        "trade_candidate": pipeline_result.trade_candidate,
        "ensemble_decision": ensemble_decision,
        "ml_prediction": ml_prediction,
        "risk_decision": risk_decision,
        "allocation": allocation,
        "execution_request": execution_request,
        "execution_result": execution_result,
        "recommendation": recommendation,
    }
