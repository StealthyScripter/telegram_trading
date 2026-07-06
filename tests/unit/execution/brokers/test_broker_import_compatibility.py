from brokers.oanda import OandaBroker as LegacyOandaBroker
from execution.brokers.oanda import OandaBroker as ExecutionOandaBroker


def test_oanda_import_compatibility():
    assert ExecutionOandaBroker is LegacyOandaBroker
