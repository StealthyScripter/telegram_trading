from datetime import datetime, timezone

from contracts.parsed_signal import ParsedSignal, ParsedSignalStatus
from decision.channel_intelligence import (
    ChannelIntelligence,
    ChannelIntelligenceConfig,
    ChannelProfileStore,
    EventLedger,
    PromotionThresholds,
)


def make_test_config():
    return ChannelIntelligenceConfig(
        thresholds=PromotionThresholds(
            minimum_signals=3,
            minimum_win_rate=0.5,
            minimum_expectancy=0.1,
            minimum_rr=0.1,
            maximum_drawdown=3.0,
            maximum_loss_streak=3,
            minimum_stability=0.1,
            minimum_profit_factor=1.1,
            pause_loss_streak=4,
            reject_loss_streak=6,
            live_score=75,
            promoting_score=65,
            paper_score=50,
        )
    )


def service(tmp_path, config=None):
    return ChannelIntelligence(
        store=ChannelProfileStore(path=str(tmp_path / "profiles.json")),
        ledger=EventLedger(path=str(tmp_path / "ledger.json")),
        config=config or make_test_config(),
    )


def parsed_signal(source="telegram_test", status=ParsedSignalStatus.VALID_SIGNAL):
    return ParsedSignal(
        raw_message_id="raw-1",
        source=source,
        status=status,
        symbol="EUR_USD" if status == ParsedSignalStatus.VALID_SIGNAL else None,
        action="buy" if status == ParsedSignalStatus.VALID_SIGNAL else None,
        stop_loss="1.1300" if status == ParsedSignalStatus.VALID_SIGNAL else None,
        take_profits=["1.1400"] if status == ParsedSignalStatus.VALID_SIGNAL else [],
        reason=None if status == ParsedSignalStatus.VALID_SIGNAL else "not valid",
    )


def trade_result(realized_r, days=1):
    return {
        "status": "CLOSED",
        "realized_r": realized_r,
        "opened_at": "2026-01-01T10:00:00+00:00",
        "closed_at": datetime(2026, 1, days, 11, 0, tzinfo=timezone.utc).isoformat(),
        "stop_distance": 0.005,
        "tp_distance": 0.01,
    }
