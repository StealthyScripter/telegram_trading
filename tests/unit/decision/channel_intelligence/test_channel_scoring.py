from decision.channel_intelligence import ChannelScorer, RollingStatistics
from tests.unit.decision.channel_intelligence.helpers import make_test_config


def test_score_is_normalized_between_zero_and_one_hundred():
    scorer = ChannelScorer(make_test_config())
    stats = RollingStatistics(
        closed_trades=10,
        wins=7,
        losses=3,
        win_rate=0.7,
        expectancy=0.6,
        profit_factor=2.0,
        max_drawdown=1.0,
        consistency_score=0.8,
    )

    score = scorer.score(stats)

    assert 0 <= score <= 100
    assert score > 50


def test_negative_expectancy_scores_poorly():
    scorer = ChannelScorer(make_test_config())
    stats = RollingStatistics(
        closed_trades=10,
        win_rate=0.8,
        expectancy=-0.8,
        profit_factor=0.5,
        max_drawdown=3.0,
        consistency_score=0.2,
    )

    assert scorer.score(stats) < 50


def test_high_win_rate_but_poor_rr_is_penalized():
    scorer = ChannelScorer(make_test_config())
    stats = RollingStatistics(
        closed_trades=20,
        win_rate=0.9,
        expectancy=-0.1,
        profit_factor=0.7,
        max_drawdown=2.0,
        consistency_score=0.6,
    )

    assert scorer.score(stats) < 70


def test_excellent_rr_low_sample_size_is_limited():
    scorer = ChannelScorer(make_test_config())
    stats = RollingStatistics(
        closed_trades=1,
        win_rate=1.0,
        expectancy=3.0,
        profit_factor=3.0,
        max_drawdown=0.0,
        consistency_score=1.0,
    )

    assert scorer.score(stats) < 100
