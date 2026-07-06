from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class BrokerCapabilities:
    supports_market_orders: bool = True
    supports_limit_orders: bool = True
    supports_trade_close: bool = True
    supports_partial_fill: bool = False
    supports_idempotency: bool = False


@dataclass(frozen=True)
class BrokerMetadata:
    broker: str
    account_id: str | None
    env: str | None
    symbol: str | None = None
    min_units: int = 1
    price_precision: int | None = None


@dataclass(frozen=True)
class NormalizedBrokerError:
    code: str
    message: str
    retryable: bool = False
    raw_error_type: str | None = None


class BaseBroker(ABC):
    env: str
    account_id: str

    @abstractmethod
    def get_price(self, symbol: str):
        raise NotImplementedError

    @abstractmethod
    def place_order(self, symbol, units, entry_price=None, take_profit=None, stop_loss=None):
        raise NotImplementedError

    @abstractmethod
    def get_open_trades(self, symbol: str | None = None):
        raise NotImplementedError

    @abstractmethod
    def get_trade(self, trade_id: str):
        raise NotImplementedError

    @abstractmethod
    def close_trade(self, trade_id: str):
        raise NotImplementedError

    @abstractmethod
    def close_open_trades(self, symbol: str | None = None):
        raise NotImplementedError

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities()

    def metadata(self, symbol: str | None = None) -> BrokerMetadata:
        return BrokerMetadata(
            broker=self.__class__.__name__,
            account_id=getattr(self, "account_id", None),
            env=getattr(self, "env", None),
            symbol=symbol,
        )

    def normalize_error(self, error: Exception) -> NormalizedBrokerError:
        retryable = isinstance(error, TimeoutError)
        return NormalizedBrokerError(
            code="BROKER_TIMEOUT" if retryable else "BROKER_ERROR",
            message=str(error),
            retryable=retryable,
            raw_error_type=error.__class__.__name__,
        )


Broker = BaseBroker
