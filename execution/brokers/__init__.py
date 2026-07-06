from execution.brokers.base import BaseBroker, Broker

__all__ = ["BaseBroker", "Broker", "OandaBroker", "PaperBroker"]


def __getattr__(name):
    if name == "OandaBroker":
        from execution.brokers.oanda import OandaBroker

        return OandaBroker

    if name == "PaperBroker":
        from execution.brokers.paper import PaperBroker

        return PaperBroker

    raise AttributeError(name)
