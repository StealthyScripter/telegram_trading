import inspect

from capital.allocator import CapitalAllocator
from decision.ml_model import MLModel
from execution.execution_service import ExecutionService
from learning.recommendation_engine import RecommendationEngine
from parsing.parser import SignalParser
from risk.risk_engine import RiskEngine


def public_methods(cls) -> set[str]:
    return {
        name for name, value in inspect.getmembers(cls, inspect.isfunction)
        if not name.startswith("_")
    }


def assert_no_public_method_patterns(cls, forbidden_patterns: tuple[str, ...]):
    violations = [
        name for name in public_methods(cls)
        if any(pattern in name.lower() for pattern in forbidden_patterns)
    ]
    assert violations == []


def test_execution_service_only_exposes_execution_boundary():
    assert public_methods(ExecutionService) == {"execute"}
    assert_no_public_method_patterns(
        ExecutionService,
        ("parse", "decide", "risk", "allocate", "train", "telegram"),
    )


def test_parser_does_not_expose_execution_or_risk_responsibilities():
    assert "parse_raw_message" in public_methods(SignalParser)
    assert_no_public_method_patterns(
        SignalParser,
        ("execute", "broker", "allocate", "risk", "train"),
    )


def test_risk_engine_does_not_expose_parse_or_execution_responsibilities():
    assert public_methods(RiskEngine) == {"evaluate"}
    assert_no_public_method_patterns(
        RiskEngine,
        ("telegram", "parse", "execute", "broker", "order"),
    )


def test_capital_allocator_does_not_expose_parse_or_broker_responsibilities():
    assert {"allocate", "decide"}.issubset(public_methods(CapitalAllocator))
    assert_no_public_method_patterns(
        CapitalAllocator,
        ("telegram", "parse", "broker", "execute_live"),
    )


def test_ml_model_does_not_expose_execution_responsibilities():
    assert "score" in public_methods(MLModel)
    assert_no_public_method_patterns(
        MLModel,
        ("execute", "broker", "order", "trade_live"),
    )


def test_learning_does_not_expose_execution_responsibilities():
    assert public_methods(RecommendationEngine) == {"recommend"}
    assert_no_public_method_patterns(
        RecommendationEngine,
        ("execute", "broker", "place_order", "close_trade"),
    )
