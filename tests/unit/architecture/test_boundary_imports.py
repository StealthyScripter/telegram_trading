import inspect

from capital import allocator as capital_allocator
from decision import ml_model
from execution import trade_executor
from parsing import parser
from risk import risk_engine


def test_parser_does_not_import_execution_or_brokers():
    source = inspect.getsource(parser)

    for forbidden in ["TradeExecutor", "BrokerFactory", "OandaBroker", "PaperBroker"]:
        assert forbidden not in source


def test_ml_does_not_import_execution_or_brokers():
    source = inspect.getsource(ml_model)

    for forbidden in ["TradeExecutor", "BrokerFactory", "OandaBroker", "PaperBroker"]:
        assert forbidden not in source


def test_risk_does_not_import_telegram_parser_brokers_or_execution():
    source = inspect.getsource(risk_engine)

    for forbidden in ["Telegram", "RawMessage", "SignalParser", "TradeExecutor", "BrokerFactory", "OandaBroker"]:
        assert forbidden not in source


def test_capital_does_not_parse_raw_signals_or_call_brokers():
    source = inspect.getsource(capital_allocator)

    for forbidden in ["RawMessage", "SignalParser", "BrokerFactory", "OandaBroker", "PaperBroker"]:
        assert forbidden not in source


def test_execution_does_not_import_parser_decision_ml_risk_or_capital():
    source = inspect.getsource(trade_executor)

    for forbidden in ["SignalParser", "DecisionEngine", "MLModel", "RiskEngine", "CapitalAllocator"]:
        assert forbidden not in source
