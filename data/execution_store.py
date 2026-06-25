import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


class ExecutionStore:
    def __init__(self, path: str = "data/execution_state.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self._write({"executions": []})

    def _read(self) -> dict:
        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _write(self, data: dict):
        fd, temp_path = tempfile.mkstemp(
            dir=str(self.path.parent),
            prefix=".execution_state_",
            suffix=".json",
        )

        with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
            json.dump(data, temp_file, indent=2, default=str)

        os.replace(temp_path, self.path)

    def create_attempt(self, request_id: str, payload: dict):
        data = self._read()

        record = {
            "request_id": request_id,
            "idempotency_key": payload.get("idempotency_key"),
            "event_type": "TRADE_OPEN",
            "status": "ATTEMPT_STARTED",
            "broker": payload.get("broker"),
            "broker_env": payload.get("broker_env"),
            "account_id": payload.get("account_id"),
            "symbol": payload.get("symbol"),
            "action": payload.get("action"),
            "units": payload.get("units"),
            "source": payload.get("source"),
            "strategy": payload.get("strategy"),
            "route_reason": payload.get("route_reason"),
            "entry_price": payload.get("entry_price"),
            "expected_entry_price": payload.get("expected_entry_price"),
            "take_profit": payload.get("take_profit"),
            "stop_loss": payload.get("stop_loss"),
            "open_trade_policy": payload.get("open_trade_policy"),
            "broker_trade_id": None,
            "broker_order_id": None,
            "reason": None,
            "realized_pl": None,
            "close_price": None,
            "closed_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "raw_response": None,
        }

        data["executions"].append(record)
        self._write(data)

    def update_attempt(self, request_id: str, updates: dict):
        data = self._read()

        for record in data["executions"]:
            if record["request_id"] == request_id:
                record.update(updates)
                record["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._write(data)
                return

        raise ValueError(f"No execution found for request_id: {request_id}")

    def create_close_attempt(self, request_id: str, payload: dict):
        data = self._read()

        record = {
            "request_id": request_id,
            "event_type": "TRADE_CLOSE",
            "status": "CLOSE_ATTEMPT_STARTED",
            "broker": payload.get("broker"),
            "broker_env": payload.get("broker_env"),
            "account_id": payload.get("account_id"),
            "symbol": payload.get("symbol"),
            "broker_trade_id": payload.get("broker_trade_id"),
            "source": payload.get("source"),
            "strategy": payload.get("strategy"),
            "reason": payload.get("reason"),
            "realized_pl": None,
            "close_price": None,
            "closed_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "raw_response": None,
        }

        data["executions"].append(record)
        self._write(data)

    def update_close_attempt(self, request_id: str, updates: dict):
        self.update_attempt(request_id, updates)

    def get_unfinished_attempts(self):
        unfinished_statuses = {
            "ATTEMPT_STARTED",
            "BROKER_REQUEST_SENT",
            "BROKER_RESPONSE_RECEIVED",
            "CLOSE_ATTEMPT_STARTED",
            "CLOSE_REQUEST_SENT",
            "CLOSE_RESPONSE_RECEIVED",
        }

        return [
            record for record in self.all_executions()
            if record.get("status") in unfinished_statuses
        ]

    def all_executions(self):
        return self._read().get("executions", [])
    