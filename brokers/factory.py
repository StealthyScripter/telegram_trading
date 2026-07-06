from brokers.oanda import OandaBroker
from execution.brokers.paper import PaperBroker


class BrokerFactory:
    def create(self, broker_name: str, account_id: str):
        if broker_name == "oanda":
            return OandaBroker(account_id=account_id)

        if broker_name == "paper":
            return PaperBroker(account_id=account_id)

        raise ValueError(f"Unsupported broker: {broker_name}")
