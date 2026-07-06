from risk.exposure import OpenPosition
from risk.portfolio import PortfolioRisk, PortfolioState, RiskPolicy


def test_portfolio_snapshot_delegates_to_exposure():
    state = PortfolioState(
        account_id="acct-1",
        broker="oanda",
        equity=10000,
        open_positions=[
            OpenPosition("EUR_USD", "alpha", "oanda", "acct-1", 1000, 50),
        ],
    )

    snapshot = PortfolioRisk().snapshot(state)

    assert snapshot.total_open_trades == 1
    assert snapshot.total_risk == 50


def test_risk_policy_is_configurable():
    policy = RiskPolicy(max_open_trades=2, max_daily_risk=100)

    assert policy.max_open_trades == 2
    assert policy.max_daily_risk == 100
