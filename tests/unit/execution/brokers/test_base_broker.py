import pytest

from execution.brokers.base import BaseBroker


def test_base_broker_interface_requires_methods():
    with pytest.raises(TypeError):
        BaseBroker()
