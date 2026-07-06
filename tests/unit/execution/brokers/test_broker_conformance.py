from execution.brokers.base import BrokerCapabilities, BrokerMetadata, NormalizedBrokerError
from execution.brokers.paper import PaperBroker


def test_paper_broker_conformance_suite_open_close_price_metadata():
    broker = PaperBroker(account_id="paper-1", price=1.2)

    price = broker.get_price("EUR_USD")
    order = broker.place_order("EUR_USD", 1000, stop_loss="1.1900", take_profit="1.2200")
    trade_id = order["orderFillTransaction"]["tradeOpened"]["tradeID"]
    close = broker.close_trade(trade_id)

    assert price["tradeable"] is True
    assert broker.get_trade(trade_id)["state"] == "CLOSED"
    assert close["orderFillTransaction"]["tradesClosed"][0]["tradeID"] == trade_id
    assert isinstance(broker.capabilities(), BrokerCapabilities)
    assert isinstance(broker.metadata("EUR_USD"), BrokerMetadata)


def test_paper_broker_partial_failure_is_normalized():
    broker = PaperBroker()

    normalized = broker.normalize_error(RuntimeError("provider raw response"))

    assert isinstance(normalized, NormalizedBrokerError)
    assert normalized.code == "BROKER_REJECTED"
    assert normalized.message == "provider raw response"


def test_paper_broker_missing_trade_close_is_safe_noop():
    broker = PaperBroker()

    response = broker.close_trade("missing")

    assert response["orderFillTransaction"]["tradesClosed"] == []
