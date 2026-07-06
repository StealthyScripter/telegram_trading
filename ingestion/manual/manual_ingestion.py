from datetime import datetime, timezone

from contracts.raw_message import RawMessage


class ManualSignalIngestor:
    def ingest(
        self,
        raw_text: str,
        source: str = "manual",
        message_id: str | None = None,
        source_title: str | None = None,
    ) -> RawMessage:
        now = datetime.now(timezone.utc).isoformat()
        return RawMessage(
            source=source,
            source_type="manual",
            source_title=source_title,
            message_id=message_id or f"manual-{now}",
            posted_at=now,
            received_at=now,
            raw_text=raw_text,
        )
