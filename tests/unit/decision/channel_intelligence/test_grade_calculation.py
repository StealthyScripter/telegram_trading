from decision.channel_intelligence import ChannelGrade
from tests.unit.decision.channel_intelligence.helpers import service, trade_result


def test_one_trade_remains_observe(tmp_path):
    intelligence = service(tmp_path)

    intelligence.record_trade_result("telegram_alpha", trade_result(5))
    context = intelligence.evaluate_source("telegram_alpha")

    assert context.grade == ChannelGrade.OBSERVE


def test_drawdown_pauses_channel(tmp_path):
    intelligence = service(tmp_path)

    for value in [1, 1, -5]:
        intelligence.record_trade_result("telegram_alpha", trade_result(value))

    context = intelligence.evaluate_source("telegram_alpha")

    assert context.grade == ChannelGrade.PAUSED


def test_backtest_updates_channel_profile(tmp_path):
    intelligence = service(tmp_path)

    profile = intelligence.record_backtest_result(
        "telegram_backtest",
        trade_result(1.25),
    )

    assert profile.rolling_statistics.executed_paper == 1
    assert profile.rolling_statistics.wins == 1
