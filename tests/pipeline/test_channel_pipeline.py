from contracts.raw_message import RawMessage
from contracts.trade_candidate import TradeCandidateStatus
from decision.channel_intelligence import ChannelIntelligence, ChannelProfileStore, EventLedger, ManualOverride
from decision.decision_engine import DecisionEngine
from orchestration.backtest_pipeline import BacktestPipeline
from orchestration.pipeline import Pipeline
from tests.unit.decision.channel_intelligence.helpers import trade_result
from tests.unit.decision.channel_intelligence.helpers import make_test_config


def make_raw_message(text: str) -> RawMessage:
    return RawMessage(
        source="telegram_channel",
        message_id="1",
        posted_at="2026-01-01T10:00:00+00:00",
        received_at="2026-01-01T10:00:01+00:00",
        raw_text=text,
    )


def test_channel_pipeline_applies_channel_intelligence(tmp_path):
    intelligence = ChannelIntelligence(
        store=ChannelProfileStore(path=str(tmp_path / "profiles.json")),
        ledger=EventLedger(path=str(tmp_path / "channel_ledger.json")),
        config=make_test_config(),
    )
    intelligence.set_manual_override("telegram_channel", ManualOverride.FORCE_PAPER)

    pipeline = Pipeline(
        decision_engine=DecisionEngine(channel_intelligence=intelligence),
        ledger=EventLedger(path=str(tmp_path / "pipeline_ledger.json")),
    )

    result = pipeline.run(make_raw_message("BUY EURUSD SL 1.1300 TP 1.1400"))

    assert result.trade_candidate.status == TradeCandidateStatus.PAPER_ONLY
    assert intelligence.store.get("telegram_channel").rolling_statistics.valid_signals == 1
    assert intelligence.ledger.find_by_stage("channel_intelligence")


def test_backtest_pipeline_feeds_channel_profile(tmp_path):
    intelligence = ChannelIntelligence(
        store=ChannelProfileStore(path=str(tmp_path / "profiles.json")),
        ledger=EventLedger(path=str(tmp_path / "channel_ledger.json")),
        config=make_test_config(),
    )
    pipeline = Pipeline(ledger=EventLedger(path=str(tmp_path / "pipeline_ledger.json")))

    BacktestPipeline(
        pipeline=pipeline,
        channel_intelligence=intelligence,
    ).replay_raw_message(
        make_raw_message("BUY EURUSD SL 1.1300 TP 1.1400"),
        backtest_result=trade_result(1.5),
    )

    profile = intelligence.store.get("telegram_channel")

    assert profile.rolling_statistics.executed_paper == 1
    assert profile.rolling_statistics.wins == 1
