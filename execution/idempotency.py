import hashlib
import time
from datetime import datetime, timezone, timedelta

from data.execution_store import ExecutionStore


class InMemoryIdempotencyStore:
    def __init__(self):
        self.seen: dict[str, float] = {}

    def make_key(self, trade) -> str:
        raw = "|".join([
            trade.broker,
            str(trade.broker_account_id),
            str(trade.strategy_account),
            trade.symbol,
            trade.action,
            str(trade.units),
            str(trade.entry_price),
            str(trade.take_profit),
            str(trade.stop_loss),
            str(trade.source),
            str(trade.external_signal_id),
        ])

        return hashlib.sha256(raw.encode()).hexdigest()

    def exists(self, key: str, window_seconds: int = 300) -> bool:
        now = time.time()
        created = self.seen.get(key)

        if not created:
            return False

        return now - created <= window_seconds

    def record(self, key: str):
        self.seen[key] = time.time()


class PersistentIdempotencyStore:
    def __init__(self):
        self.store = ExecutionStore()

    def make_key(self, trade) -> str:
        raw = "|".join([
            trade.broker,
            str(trade.broker_account_id),
            str(trade.strategy_account),
            trade.symbol,
            trade.action,
            str(trade.units),
            str(trade.entry_price),
            str(trade.take_profit),
            str(trade.stop_loss),
            str(trade.source),
            str(trade.external_signal_id),
        ])

        return hashlib.sha256(raw.encode()).hexdigest()

    def exists(self, key: str, window_seconds: int = 300) -> bool:
        now = datetime.now(timezone.utc)

        for record in self.store.all_executions():
            if record.get("idempotency_key") != key:
                continue

            created_at = record.get("created_at")

            if not created_at:
                return True

            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

            if now - created <= timedelta(seconds=window_seconds):
                return True

        return False
