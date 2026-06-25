import pytest

from config.instruments import get_instrument_meta
from controls.bot_controls import BotControls
from controls.trade_controls import OpenTradePolicy, TradeControls
from execution.account_router import AccountRouter


def test_kill_switch_blocks_trading(monkeypatch):
    monkeypatch.setenv("BOT_KILL_SWITCH", "true")

    controls = BotControls()

    with pytest.raises(RuntimeError, match="BOT_KILL_SWITCH"):
        controls.assert_can_trade("practice")


def test_live_trading_blocked_without_flag(monkeypatch):
    monkeypatch.setenv("BOT_KILL_SWITCH", "false")
    monkeypatch.setenv("ALLOW_LIVE_TRADING", "false")

    controls = BotControls()

    with pytest.raises(RuntimeError, match="Live trading blocked"):
        controls.assert_can_trade("live")


def test_live_trading_allowed_with_flag(monkeypatch):
    monkeypatch.setenv("BOT_KILL_SWITCH", "false")
    monkeypatch.setenv("ALLOW_LIVE_TRADING", "true")

    controls = BotControls()
    controls.assert_can_trade("live")


def test_instrument_metadata_eur_usd():
    meta = get_instrument_meta("EUR_USD")

    assert meta.pip_size == 0.0001
    assert meta.price_precision == 5
    assert meta.min_units == 1


def test_account_router_uses_explicit_account_first(monkeypatch):
    monkeypatch.setenv("OANDA_DEFAULT_ACCOUNT", "default-acct")
    monkeypatch.setenv("OANDA_ACCOUNT_SCALPING", "scalping-acct")

    router = AccountRouter()

    assert router.resolve_account_id(
        broker_name="oanda",
        strategy_account="scalping",
        explicit_account_id="explicit-acct",
    ) == "explicit-acct"


def test_account_router_uses_strategy_account(monkeypatch):
    monkeypatch.setenv("OANDA_ACCOUNT_SCALPING", "scalping-acct")

    router = AccountRouter()

    assert router.resolve_account_id(
        broker_name="oanda",
        strategy_account="scalping",
    ) == "scalping-acct"


def test_account_router_uses_default_account(monkeypatch):
    monkeypatch.setenv("OANDA_DEFAULT_ACCOUNT", "default-acct")

    router = AccountRouter()

    assert router.resolve_account_id(
        broker_name="oanda",
    ) == "default-acct"


def test_reject_if_existing_trade_policy_blocks():
    class FakeBroker:
        def get_open_trades(self, symbol=None):
            return [{"id": "1", "instrument": symbol}]

    controls = TradeControls()

    with pytest.raises(RuntimeError, match="Open trade already exists"):
        controls.enforce_open_trade_policy(
            broker=FakeBroker(),
            symbol="EUR_USD",
            policy=OpenTradePolicy.REJECT_IF_EXISTS,
        )


def test_close_existing_first_policy_closes():
    class FakeBroker:
        def __init__(self):
            self.closed = False

        def get_open_trades(self, symbol=None):
            return [{"id": "1", "instrument": symbol}]

        def close_open_trades(self, symbol=None):
            self.closed = True

    broker = FakeBroker()
    controls = TradeControls()

    controls.enforce_open_trade_policy(
        broker=broker,
        symbol="EUR_USD",
        policy=OpenTradePolicy.CLOSE_EXISTING_FIRST,
    )

    assert broker.closed is True


def test_allow_add_policy_does_not_close_or_raise():
    class FakeBroker:
        def get_open_trades(self, symbol=None):
            return [{"id": "1", "instrument": symbol}]

    controls = TradeControls()

    controls.enforce_open_trade_policy(
        broker=FakeBroker(),
        symbol="EUR_USD",
        policy=OpenTradePolicy.ALLOW_ADD,
    )
    