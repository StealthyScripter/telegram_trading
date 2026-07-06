from ingestion.webhooks.webhook_ingestion import WebhookSignalIngestor


class TradingViewSignalIngestor(WebhookSignalIngestor):
    def ingest(self, payload: dict):
        payload = dict(payload)
        payload.setdefault("source", "tradingview")
        message = payload.get("message") or payload.get("text") or payload.get("signal")
        if not message and payload.get("symbol") and payload.get("action"):
            message = f"{payload['action']} {payload['symbol']}"
            payload["message"] = message
        raw_message = super().ingest(payload)
        if raw_message is None:
            return None
        return raw_message
