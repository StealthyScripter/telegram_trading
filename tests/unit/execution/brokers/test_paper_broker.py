from execution.brokers.paper import PaperBroker


def test_paper_broker_place_order_opens_trade():
    broker = PaperBroker(account_id="paper-1")

    response = broker.place_order(
        symbol="EUR_USD",
        units=1000,
        take_profit="1.1100",
        stop_loss="1.0950",
    )

    trade_id = response["orderFillTransaction"]["tradeOpened"]["tradeID"]

    assert broker.get_trade(trade_id)["state"] == "OPEN"
    assert len(broker.get_open_trades("EUR_USD")) == 1


def test_paper_broker_close_trade():
    broker = PaperBroker(account_id="paper-1")
    response = broker.place_order("EUR_USD", 1000)
    trade_id = response["orderFillTransaction"]["tradeOpened"]["tradeID"]

    close_response = broker.close_trade(trade_id)

    assert close_response["orderFillTransaction"]["tradesClosed"][0]["tradeID"] == trade_id
    assert broker.get_trade(trade_id)["state"] == "CLOSED"
    assert broker.get_open_trades() == []


def test_paper_broker_get_price():
    price = PaperBroker(price=1.25).get_price("EUR_USD")

    assert price["tradeable"] is True
    assert price["bid"] < price["ask"]


def test_paper_broker_capability_discovery():
    capabilities = PaperBroker().capabilities()

    assert capabilities.supports_market_orders is True
    assert capabilities.supports_limit_orders is True
    assert capabilities.supports_trade_close is True
    assert capabilities.supports_idempotency is True


def test_paper_broker_metadata_normalization():
    metadata = PaperBroker(account_id="paper-1").metadata("EUR_USD")

    assert metadata.broker == "paper"
    assert metadata.account_id == "paper-1"
    assert metadata.env == "paper"
    assert metadata.symbol == "EUR_USD"
    assert metadata.price_precision == 5
    assert metadata.min_units == 1


def test_paper_broker_timeout_normalizes_safely():
    error = PaperBroker().normalize_error(TimeoutError("slow"))

    assert error.code == "BROKER_TIMEOUT"
    assert error.retryable is True
    assert "slow" not in error.message


def test_paper_broker_rejection_normalizes_without_raw_leak():
    error = PaperBroker().normalize_error(RuntimeError("raw provider stack"))

    assert error.code == "BROKER_REJECTED"
    assert error.retryable is False
    assert error.raw_error_type == "RuntimeError"
