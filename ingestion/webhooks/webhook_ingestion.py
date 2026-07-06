from datetime import datetime, timezone

from contracts.raw_message import RawMessage


class WebhookSignalIngestor:
    def ingest(self, payload: dict) -> RawMessage | None:
        raw_text = payload.get("text") or payload.get("message") or payload.get("signal")
        if not raw_text or not str(raw_text).strip():
            return None

        now = datetime.now(timezone.utc).isoformat()
        source = str(payload.get("source") or "webhook")
        message_id = str(payload.get("message_id") or payload.get("id") or f"webhook-{now}")

        return RawMessage(
            source=source,
            source_type="webhook",
            source_title=payload.get("source_title"),
            message_id=message_id,
            posted_at=str(payload.get("posted_at") or now),
            received_at=now,
            raw_text=str(raw_text),
        )
