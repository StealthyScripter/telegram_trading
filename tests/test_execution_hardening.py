import pytest
from datetime import datetime, timezone, timedelta

from execution.idempotency import PersistentIdempotencyStore
from execution.models import TradeRequest, ExecutionResult, ExecutionStatus
from execution.validation import TradeValidator
from reconciliation.broker_reconciler import BrokerReconciler


def make_trade(**overrides):
    data = {
        "symbol": "EUR_USD",
        "action": "buy",
        "units": 1000,
        "source": "pytest",
        "strategy_account": "scalping",
        "take_profit": "1.1400",
        "stop_loss": "1.1300",
        "external_signal_id": "abc-123",
    }
    data.update(overrides)
    return TradeRequest(**data)


def fresh_quote():
    return {
        "bid": 1.1349,
        "ask": 1.1351,
        "mid": 1.1350,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tradeable": True,
    }


def stale_quote():
    quote = fresh_quote()
    quote["timestamp"] = (
        datetime.now(timezone.utc) - timedelta(seconds=999)
    ).isoformat()
    return quote


def test_persistent_idempotency_key_is_stable():
    store = PersistentIdempotencyStore()
    trade = make_trade()

    key_1 = store.make_key(trade)
    key_2 = store.make_key(trade)

    assert key_1 == key_2


def test_persistent_idempotency_key_changes_with_signal_id():
    store = PersistentIdempotencyStore()

    trade_1 = make_trade(external_signal_id="one")
    trade_2 = make_trade(external_signal_id="two")

    assert store.make_key(trade_1) != store.make_key(trade_2)


def test_buy_tp_sl_direction_valid():
    validator = TradeValidator()
    trade = make_trade(action="buy", take_profit="1.1400", stop_loss="1.1300")

    validator.validate_tp_sl_direction(trade, current_price=1.1350)


def test_buy_rejects_tp_below_price():
    validator = TradeValidator()
    trade = make_trade(action="buy", take_profit="1.1300", stop_loss="1.1200")

    with pytest.raises(ValueError, match="Buy take profit"):
        validator.validate_tp_sl_direction(trade, current_price=1.1350)


def test_buy_rejects_sl_above_price():
    validator = TradeValidator()
    trade = make_trade(action="buy", take_profit="1.1400", stop_loss="1.1360")

    with pytest.raises(ValueError, match="Buy stop loss"):
        validator.validate_tp_sl_direction(trade, current_price=1.1350)


def test_sell_tp_sl_direction_valid():
    validator = TradeValidator()
    trade = make_trade(action="sell", take_profit="1.1300", stop_loss="1.1400")

    validator.validate_tp_sl_direction(trade, current_price=1.1350)


def test_sell_rejects_tp_above_price():
    validator = TradeValidator()
    trade = make_trade(action="sell", take_profit="1.1400", stop_loss="1.1450")

    with pytest.raises(ValueError, match="Sell take profit"):
        validator.validate_tp_sl_direction(trade, current_price=1.1350)


def test_sell_rejects_sl_below_price():
    validator = TradeValidator()
    trade = make_trade(action="sell", take_profit="1.1300", stop_loss="1.1340")

    with pytest.raises(ValueError, match="Sell stop loss"):
        validator.validate_tp_sl_direction(trade, current_price=1.1350)


def test_rejects_stale_quote_using_symbol_metadata():
    validator = TradeValidator()

    with pytest.raises(ValueError, match="Quote is stale"):
        validator.validate_quote_freshness(stale_quote(), symbol="EUR_USD")


def test_accepts_fresh_quote_using_symbol_metadata():
    validator = TradeValidator()

    validator.validate_quote_freshness(fresh_quote(), symbol="EUR_USD")


def test_rejects_wide_spread_using_symbol_metadata():
    validator = TradeValidator()

    quote = fresh_quote()
    quote["bid"] = 1.1300
    quote["ask"] = 1.1400

    with pytest.raises(ValueError, match="Spread too wide"):
        validator.validate_spread(quote, symbol="EUR_USD")


def test_rejects_missing_symbol():
    validator = TradeValidator()
    trade = make_trade(symbol="")

    with pytest.raises(ValueError, match="Symbol is required"):
        validator.validate_basic(trade)


def test_rejects_zero_units():
    validator = TradeValidator()
    trade = make_trade(units=0)

    with pytest.raises(ValueError, match="Units below minimum"):
        validator.validate_basic(trade)


def test_reconciler_accepts_matching_broker_state():
    class FakeBroker:
        def get_trade(self, trade_id):
            return {"id": trade_id, "instrument": "EUR_USD"}

    result = ExecutionResult(
        status=ExecutionStatus.FILLED,
        broker="oanda",
        account_id="acct-1",
        symbol="EUR_USD",
        action="buy",
        requested_units=1000,
        broker_trade_id="123",
    )

    reconciler = BrokerReconciler()
    verified = reconciler.verify_execution(FakeBroker(), result)

    assert verified.status == ExecutionStatus.FILLED


def test_reconciler_flags_missing_broker_trade():
    class FakeBroker:
        def get_trade(self, trade_id):
            return None

    result = ExecutionResult(
        status=ExecutionStatus.FILLED,
        broker="oanda",
        account_id="acct-1",
        symbol="EUR_USD",
        action="buy",
        requested_units=1000,
        broker_trade_id="123",
    )

    reconciler = BrokerReconciler()
    verified = reconciler.verify_execution(FakeBroker(), result)

    assert verified.status == ExecutionStatus.DISCREPANCY
    assert "missing from broker state" in verified.reason


def test_reconciler_flags_symbol_mismatch():
    class FakeBroker:
        def get_trade(self, trade_id):
            return {"id": trade_id, "instrument": "GBP_USD"}

    result = ExecutionResult(
        status=ExecutionStatus.FILLED,
        broker="oanda",
        account_id="acct-1",
        symbol="EUR_USD",
        action="buy",
        requested_units=1000,
        broker_trade_id="123",
    )

    reconciler = BrokerReconciler()
    verified = reconciler.verify_execution(FakeBroker(), result)

    assert verified.status == ExecutionStatus.DISCREPANCY
    assert "symbol mismatch" in verified.reason


def test_account_router_strategy_route(monkeypatch):
    monkeypatch.setenv("OANDA_ACCOUNT_SCALPING", "acct-scalping")
    monkeypatch.setenv("OANDA_ACCOUNT_DAY_TRADING", "acct-day")

    from execution.account_router import AccountRouter

    router = AccountRouter()

    assert router.resolve_account_id(
        broker_name="oanda",
        strategy_account="scalping",
    ) == "acct-scalping"

    assert router.resolve_account_id(
        broker_name="oanda",
        strategy_account="day_trading",
    ) == "acct-day"


def test_missing_strategy_account_raises(monkeypatch):
    monkeypatch.delenv("OANDA_ACCOUNT_LONG_TERM", raising=False)

    from execution.account_router import AccountRouter

    router = AccountRouter()

    with pytest.raises(ValueError, match="No oanda account configured|No OANDA account configured"):
        router.resolve_account_id(
            broker_name="oanda",
            strategy_account="long_term",
        )
