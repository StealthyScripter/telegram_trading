from backtesting.channel_scorecard import ChannelScorecard


def test_channel_scorecard_scores_closed_trades():
    scorecard = ChannelScorecard()

    trades = [
        {"status": "CLOSED", "realized_r": 2},
        {"status": "CLOSED", "realized_r": -1},
        {"status": "CLOSED", "realized_r": 1},
    ]

    result = scorecard.score(trades)

    assert result["total_trades"] == 3
    assert result["wins"] == 2
    assert result["losses"] == 1
    assert result["net_r"] == 2
    assert result["profit_factor"] == 3
    