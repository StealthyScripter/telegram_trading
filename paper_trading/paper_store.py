import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


class PaperTradeStore:
    def __init__(self, path: str = "data/paper_trades.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self._write({"paper_trades": []})

    def _read(self):
        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _write(self, data):
        fd, temp_path = tempfile.mkstemp(
            dir=str(self.path.parent),
            prefix=".paper_trades_",
            suffix=".json",
        )

        with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
            json.dump(data, temp_file, indent=2, default=str)

        os.replace(temp_path, self.path)

    def create_paper_trade(self, signal: dict):
        data = self._read()
        parsed = signal["parsed_signal"]

        record = {
            "paper_trade_id": signal["signal_id"],
            "signal_id": signal["signal_id"],
            "source": signal["source"],
            "symbol": parsed["symbol"],
            "action": parsed["action"],
            "entry_price": parsed["entry_price"],
            "stop_loss": parsed["stop_loss"],
            "take_profits": parsed["take_profits"],
            "status": "OPEN",
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "closed_at": None,
            "close_price": None,
            "result": None,
            "realized_r": None,
            "raw_signal": signal,
        }

        data["paper_trades"].append(record)
        self._write(data)
        return record

    def all_trades(self):
        return self._read()["paper_trades"]
    