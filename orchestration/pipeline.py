from dataclasses import dataclass

from contracts.raw_message import RawMessage
from contracts.trade_candidate import TradeCandidate
from decision.decision_engine import DecisionEngine
from events.ledger import EventLedger
from events.models import DecisionEvent
from parsing.parser import SignalParser


@dataclass(frozen=True)
class PipelineResult:
    raw_message: RawMessage
    parsed_signal: object
    trade_candidate: TradeCandidate
    execution_result: object | None = None


class Pipeline:
    def __init__(
        self,
        parser: SignalParser | None = None,
        decision_engine: DecisionEngine | None = None,
        ledger: EventLedger | None = None,
        execution_service=None,
    ):
        self.parser = parser or SignalParser()
        self.decision_engine = decision_engine or DecisionEngine()
        self.ledger = ledger or EventLedger()
        self.execution_service = execution_service

    def run(self, raw_message: RawMessage, execution_request=None) -> PipelineResult:
        parsed_signal = self.parser.parse_raw_message(raw_message)
        self.ledger.append(
            DecisionEvent(
                stage="parsing",
                input_id=raw_message.id,
                output_id=parsed_signal.id,
                reason=parsed_signal.reason,
                payload=parsed_signal.to_dict(),
            )
        )

        trade_candidate = self.decision_engine.evaluate(parsed_signal)
        self.ledger.append(
            DecisionEvent(
                stage="decision",
                input_id=parsed_signal.id,
                output_id=trade_candidate.id,
                reason=trade_candidate.reason,
                payload=trade_candidate.to_dict(),
            )
        )

        execution_result = None
        if self.execution_service is not None and execution_request is not None:
            execution_result = self.execution_service.execute(execution_request)
            self.ledger.append(
                DecisionEvent(
                    stage="execution",
                    input_id=execution_request.id,
                    output_id=execution_result.id,
                    reason=execution_result.reason,
                    payload=execution_result.to_dict(),
                )
            )

        return PipelineResult(
            raw_message=raw_message,
            parsed_signal=parsed_signal,
            trade_candidate=trade_candidate,
            execution_result=execution_result,
        )
