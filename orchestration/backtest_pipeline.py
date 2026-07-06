from dataclasses import dataclass

from contracts.raw_message import RawMessage
from contracts.trade_candidate import TradeCandidateStatus
from orchestration.pipeline import Pipeline


@dataclass(frozen=True)
class BacktestPipelineResult:
    raw_message: RawMessage
    parsed_signal: object
    trade_candidate: object
    simulated_result: dict | None


class BacktestPipeline:
    def __init__(self, pipeline: Pipeline | None = None, channel_intelligence=None):
        self.pipeline = pipeline or Pipeline()
        self.channel_intelligence = channel_intelligence

    def replay_raw_message(
        self,
        raw_message: RawMessage,
        backtest_result: dict | None = None,
    ) -> BacktestPipelineResult:
        result = self.pipeline.run(raw_message)

        simulated_result = None
        if result.trade_candidate.status == TradeCandidateStatus.APPROVED_FOR_RISK:
            simulated_result = {
                "status": "SIMULATED",
                "candidate_id": result.trade_candidate.id,
                "symbol": result.trade_candidate.symbol,
                "action": result.trade_candidate.action,
            }

        if self.channel_intelligence and backtest_result:
            self.channel_intelligence.record_backtest_result(
                source_name=raw_message.source,
                result=backtest_result,
            )

        return BacktestPipelineResult(
            raw_message=result.raw_message,
            parsed_signal=result.parsed_signal,
            trade_candidate=result.trade_candidate,
            simulated_result=simulated_result,
        )
