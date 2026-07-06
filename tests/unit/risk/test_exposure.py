from risk.exposure import ExposureRisk, OpenPosition


def test_exposure_snapshot_calculation():
    positions = [
        OpenPosition("EUR_USD", "alpha", "oanda", "acct-1", 1000, 50, currency="USD", strategy="scalp", correlation_group="USD"),
        OpenPosition("EUR_USD", "beta", "oanda", "acct-1", 1000, 25, currency="USD", strategy="swing", correlation_group="USD"),
        OpenPosition("GBP_USD", "alpha", "paper", "acct-2", 1000, 10, currency="USD", strategy="scalp", correlation_group="USD"),
    ]

    snapshot = ExposureRisk().calculate(positions)

    assert snapshot.total_open_trades == 3
    assert snapshot.total_risk == 85
    assert snapshot.symbol_risk["EUR_USD"] == 75
    assert snapshot.source_risk["alpha"] == 60
    assert snapshot.account_risk["acct-1"] == 75
    assert snapshot.broker_risk["oanda"] == 75
    assert snapshot.currency_risk["USD"] == 85
    assert snapshot.strategy_risk["scalp"] == 60
    assert snapshot.correlation_risk["USD"] == 85
