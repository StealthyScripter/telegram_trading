from brokers import oanda as old_oanda_module
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
