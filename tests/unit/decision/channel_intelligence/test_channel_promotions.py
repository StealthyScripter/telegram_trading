from decision.channel_intelligence import ChannelGrade, PromotionAction
from tests.unit.decision.channel_intelligence.helpers import service, trade_result


def test_promotion_after_profitable_sample(tmp_path):
    intelligence = service(tmp_path)

    for value in [1.5, 1.0, -0.5, 2.0]:
        intelligence.record_trade_result("telegram_alpha", trade_result(value))

    context = intelligence.evaluate_source("telegram_alpha")

    assert context.promotion_decision.action == PromotionAction.PROMOTE
    assert context.grade in {ChannelGrade.PAPER, ChannelGrade.PROMOTING, ChannelGrade.LIVE}
    assert context.paper_enabled is True


def test_demote_or_pause_after_negative_expectancy(tmp_path):
    intelligence = service(tmp_path)

    for value in [0.2, -1.0, -1.0, -1.0]:
        intelligence.record_trade_result("telegram_bad", trade_result(value))

    context = intelligence.evaluate_source("telegram_bad")

    assert context.grade in {ChannelGrade.OBSERVE, ChannelGrade.PAUSED}
    assert context.live_enabled is False


def test_reject_after_rejection_loss_streak(tmp_path):
    intelligence = service(tmp_path)

    for _ in range(6):
        intelligence.record_trade_result("telegram_reject", trade_result(-1))

    context = intelligence.evaluate_source("telegram_reject")

    assert context.grade == ChannelGrade.REJECTED
    assert context.promotion_decision.action == PromotionAction.REJECT
