from brokers import oanda as old_oanda_module
from brokers.oanda import OandaBroker
from brokers.factory import BrokerFactory
from execution.brokers.paper import PaperBroker


def test_broker_factory_creates_paper():
    broker = BrokerFactory().create("paper", "paper-1")

    assert isinstance(broker, PaperBroker)
    assert broker.account_id == "paper-1"


def test_broker_factory_creates_oanda_without_changing_import(monkeypatch):
    class FakeOanda:
        def __init__(self, account_id):
            self.account_id = account_id

    monkeypatch.setattr("brokers.factory.OandaBroker", FakeOanda)

    broker = BrokerFactory().create("oanda", "acct-1")

    assert isinstance(broker, FakeOanda)
    assert broker.account_id == "acct-1"
    assert hasattr(old_oanda_module, "OandaBroker")


def test_oanda_adapter_constructs_without_network(monkeypatch):
    monkeypatch.setenv("OANDA_API_TOKEN", "token")
    monkeypatch.setenv("OANDA_ENV", "practice")

    broker = OandaBroker(account_id="acct-1")

    assert broker.account_id == "acct-1"
    assert broker.env == "practice"
    assert broker.metadata("EUR_USD").broker == "oanda"
    assert broker.capabilities().supports_partial_fill is True


def test_oanda_timeout_error_normalizes_without_network(monkeypatch):
    monkeypatch.setenv("OANDA_API_TOKEN", "token")

    broker = OandaBroker(account_id="acct-1")
    error = broker.normalize_error(TimeoutError("provider detail"))

    assert error.code == "BROKER_TIMEOUT"
    assert error.retryable is True
