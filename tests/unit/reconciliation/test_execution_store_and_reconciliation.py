from pathlib import Path

from data.execution_store import ExecutionStore
from reconciliation.startup_reconciler import StartupReconciler


def test_execution_store_creates_attempt(tmp_path):
    path = tmp_path / "execution_state.json"
    store = ExecutionStore(path=str(path))

    store.create_attempt(
        request_id="req-1",
        payload={
            "broker": "oanda",
            "account_id": "acct-1",
            "symbol": "EUR_USD",
            "action": "buy",
            "units": 1000,
            "take_profit": "1.1400",
            "stop_loss": "1.1300",
        },
    )

    executions = store.all_executions()

    assert len(executions) == 1
    assert executions[0]["request_id"] == "req-1"
    assert executions[0]["status"] == "ATTEMPT_STARTED"


def test_execution_store_updates_attempt(tmp_path):
    path = tmp_path / "execution_state.json"
    store = ExecutionStore(path=str(path))

    store.create_attempt(
        request_id="req-1",
        payload={
            "broker": "oanda",
            "account_id": "acct-1",
            "symbol": "EUR_USD",
            "action": "buy",
            "units": 1000,
        },
    )

    store.update_attempt(
        request_id="req-1",
        updates={
            "status": "FILLED",
            "broker_trade_id": "123",
            "broker_order_id": "122",
        },
    )

    execution = store.all_executions()[0]

    assert execution["status"] == "FILLED"
    assert execution["broker_trade_id"] == "123"


def test_execution_store_finds_unfinished_attempts(tmp_path):
    path = tmp_path / "execution_state.json"
    store = ExecutionStore(path=str(path))

    store.create_attempt(
        request_id="req-1",
        payload={
            "broker": "oanda",
            "account_id": "acct-1",
            "symbol": "EUR_USD",
            "action": "buy",
            "units": 1000,
        },
    )

    unfinished = store.get_unfinished_attempts()

    assert len(unfinished) == 1
    assert unfinished[0]["request_id"] == "req-1"


def test_startup_reconciler_flags_unknown_broker_trade(monkeypatch, tmp_path):
    path = tmp_path / "execution_state.json"
    store = ExecutionStore(path=str(path))

    class FakeBroker:
        def __init__(self, account_id):
            self.account_id = account_id

        def get_open_trades(self, symbol=None):
            return [
                {
                    "id": "999",
                    "instrument": "EUR_USD",
                    "currentUnits": "1000",
                }
            ]

    monkeypatch.setattr(
        "reconciliation.startup_reconciler.ExecutionStore",
        lambda: store,
    )

    monkeypatch.setattr(
        "reconciliation.startup_reconciler.OandaBroker",
        FakeBroker,
    )

    reconciler = StartupReconciler()
    report = reconciler.run_for_account(
        account_id="acct-1",
        symbol="EUR_USD",
    )

    assert len(report["unknown_open_trades"]) == 1
    assert report["unknown_open_trades"][0]["id"] == "999"


def test_startup_reconciler_does_not_flag_known_trade(monkeypatch, tmp_path):
    path = tmp_path / "execution_state.json"
    store = ExecutionStore(path=str(path))

    store.create_attempt(
        request_id="req-1",
        payload={
            "broker": "oanda",
            "account_id": "acct-1",
            "symbol": "EUR_USD",
            "action": "buy",
            "units": 1000,
        },
    )

    store.update_attempt(
        request_id="req-1",
        updates={
            "status": "FILLED",
            "broker_trade_id": "999",
        },
    )

    class FakeBroker:
        def __init__(self, account_id):
            self.account_id = account_id

        def get_open_trades(self, symbol=None):
            return [
                {
                    "id": "999",
                    "instrument": "EUR_USD",
                    "currentUnits": "1000",
                }
            ]

    monkeypatch.setattr(
        "reconciliation.startup_reconciler.ExecutionStore",
        lambda: store,
    )

    monkeypatch.setattr(
        "reconciliation.startup_reconciler.OandaBroker",
        FakeBroker,
    )

    reconciler = StartupReconciler()
    report = reconciler.run_for_account(
        account_id="acct-1",
        symbol="EUR_USD",
    )

    assert report["unknown_open_trades"] == []
