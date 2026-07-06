from contracts.parsed_signal import ParsedSignal, ParsedSignalStatus
from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus
from decision.channel_intelligence import ChannelGrade, ChannelIntelligence, DecisionContext


class DecisionEngine:
    def __init__(self, channel_intelligence: ChannelIntelligence | None = None):
        self.channel_intelligence = channel_intelligence
        self.last_context: DecisionContext | None = None

    def evaluate(self, parsed_signal: ParsedSignal) -> TradeCandidate:
        context = self._channel_context(parsed_signal)

        if parsed_signal.status != ParsedSignalStatus.VALID_SIGNAL:
            return TradeCandidate(
                parsed_signal_id=parsed_signal.id,
                source=parsed_signal.source,
                status=TradeCandidateStatus.OBSERVE_ONLY,
                symbol=parsed_signal.symbol,
                action=parsed_signal.action,
                entry_type=parsed_signal.entry_type,
                entry_price=parsed_signal.entry_price,
                stop_loss=parsed_signal.stop_loss,
                take_profits=list(parsed_signal.take_profits),
                reason=parsed_signal.reason or "Signal is not valid for risk review",
            )

        if context:
            status = self._status_from_channel_context(context)
            return TradeCandidate(
                parsed_signal_id=parsed_signal.id,
                source=parsed_signal.source,
                status=status,
                symbol=parsed_signal.symbol,
                action=parsed_signal.action,
                entry_type=parsed_signal.entry_type,
                entry_price=parsed_signal.entry_price,
                stop_loss=parsed_signal.stop_loss,
                take_profits=list(parsed_signal.take_profits),
                reason=context.approval_reason,
            )

        return TradeCandidate(
            parsed_signal_id=parsed_signal.id,
            source=parsed_signal.source,
            status=TradeCandidateStatus.APPROVED_FOR_RISK,
            symbol=parsed_signal.symbol,
            action=parsed_signal.action,
            entry_type=parsed_signal.entry_type,
            entry_price=parsed_signal.entry_price,
            stop_loss=parsed_signal.stop_loss,
            take_profits=list(parsed_signal.take_profits),
            reason="Valid signal approved for risk review",
        )

    def _channel_context(self, parsed_signal: ParsedSignal):
        if not self.channel_intelligence:
            return None

        self.channel_intelligence.record_parsed_signal(parsed_signal)
        self.last_context = self.channel_intelligence.evaluate_source(parsed_signal.source)
        return self.last_context

    def _status_from_channel_context(
        self,
        context: DecisionContext,
    ) -> TradeCandidateStatus:
        if context.grade in {ChannelGrade.REJECTED, ChannelGrade.BLACKLISTED}:
            return TradeCandidateStatus.REJECTED

        if context.grade == ChannelGrade.PAPER:
            return TradeCandidateStatus.PAPER_ONLY

        if context.grade in {ChannelGrade.PROMOTING, ChannelGrade.LIVE}:
            return TradeCandidateStatus.APPROVED_FOR_RISK

        return TradeCandidateStatus.OBSERVE_ONLY
