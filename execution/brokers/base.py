from abc import ABC, abstractmethod


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


Broker = BaseBroker
