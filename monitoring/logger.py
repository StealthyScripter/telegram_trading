import json
import logging


logging.basicConfig(
    filename="execution.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


class ExecutionLogger:
    def info(self, event: str, data: dict):
        logging.info(json.dumps({"event": event, **data}, default=str))

    def warning(self, event: str, data: dict):
        logging.warning(json.dumps({"event": event, **data}, default=str))

    def error(self, event: str, data: dict):
        logging.error(json.dumps({"event": event, **data}, default=str))
