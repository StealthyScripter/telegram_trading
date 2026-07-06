import pytest

from execution.brokers.base import BaseBroker
from execution.brokers.paper import PaperBroker


def test_base_broker_interface_requires_methods():
    with pytest.raises(TypeError):
        BaseBroker()


def test_paper_broker_satisfies_base_broker_contract():
    broker = PaperBroker()

    assert isinstance(broker, BaseBroker)
    assert broker.capabilities().supports_market_orders is True
    assert broker.metadata("EUR_USD").min_units == 1
