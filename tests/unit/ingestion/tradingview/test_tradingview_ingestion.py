from ingestion.tradingview import TradingViewSignalIngestor


def test_tradingview_payload_to_raw_message_preserves_source_type():
    message = TradingViewSignalIngestor().ingest(
        {
            "id": "tv-1",
            "symbol": "EURUSD",
            "action": "BUY",
        }
    )

    assert message.source == "tradingview"
    assert message.source_type == "webhook"
    assert message.message_id == "tv-1"
    assert message.raw_text == "BUY EURUSD"
