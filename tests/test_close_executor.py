from execution.close_executor import CloseExecutor


def test_close_executor_records_success(monkeypatch, tmp_path):
    class FakeBroker:
        env = "practice"

        def close_trade(self, trade_id):
            return {
                "orderFillTransaction": {
                    "reason": "MARKET_ORDER_TRADE_CLOSE",
                    "tradesClosed": [
                        {
                            "tradeID": trade_id,
                            "price": "1.1000",
                            "realizedPL": "1.25",
                        }
                    ],
                }
            }

        def get_trade(self, trade_id):
            return None

    class FakeFactory:
        def create(self, broker_name, account_id):
            return FakeBroker()

    executor = CloseExecutor()
    executor.broker_factory = FakeFactory()

    response = executor.close_trade(
        broker_name="oanda",
        account_id="acct-1",
        trade_id="123",
        symbol="EUR_USD",
        reason="pytest",
    )

    assert response["orderFillTransaction"]["tradesClosed"][0]["tradeID"] == "123"


def test_close_executor_flags_still_open(monkeypatch):
    class FakeBroker:
        env = "practice"

        def close_trade(self, trade_id):
            return {
                "orderFillTransaction": {
                    "reason": "MARKET_ORDER_TRADE_CLOSE",
                    "tradesClosed": [{"tradeID": trade_id}],
                }
            }

        def get_trade(self, trade_id):
            return {"id": trade_id, "instrument": "EUR_USD"}

    class FakeFactory:
        def create(self, broker_name, account_id):
            return FakeBroker()

    executor = CloseExecutor()
    executor.broker_factory = FakeFactory()

    try:
        executor.close_trade(
            broker_name="oanda",
            account_id="acct-1",
            trade_id="123",
            symbol="EUR_USD",
        )
        assert False
    except RuntimeError as error:
        assert "Close discrepancy" in str(error)
