from ingestion.tradingview import TradingViewSignalIngestor
from ingestion.webhooks import WebhookSignalIngestor


def test_webhook_payload_to_raw_message():
    message = WebhookSignalIngestor().ingest(
        {
            "source": "webhook_alpha",
            "id": "webhook-1",
            "message": "SELL EURUSD SL 1.1050 TP 1.0900",
        }
    )

    assert message.source == "webhook_alpha"
    assert message.source_type == "webhook"
    assert message.message_id == "webhook-1"


def test_empty_webhook_payload_ignored():
    assert WebhookSignalIngestor().ingest({"source": "bad"}) is None


def test_tradingview_payload_scaffold_to_raw_message():
    message = TradingViewSignalIngestor().ingest(
        {
            "id": "tv-1",
            "symbol": "EURUSD",
            "action": "BUY",
        }
    )

    assert message.source == "tradingview"
    assert "BUY EURUSD" in message.raw_text
