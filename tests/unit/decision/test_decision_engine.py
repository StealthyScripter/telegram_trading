import inspect

from contracts.parsed_signal import ParsedSignal, ParsedSignalStatus
from contracts.trade_candidate import TradeCandidateStatus
from decision import decision_engine
from decision.decision_engine import DecisionEngine


def make_signal(status=ParsedSignalStatus.VALID_SIGNAL):
    return ParsedSignal(
        raw_message_id="raw-1",
        source="telegram_test",
        status=status,
        symbol="EUR_USD",
        action="buy",
        stop_loss="1.1300",
        take_profits=["1.1400"],
    )


def test_valid_signal_creates_trade_candidate():
    candidate = DecisionEngine().evaluate(make_signal())

    assert candidate.status == TradeCandidateStatus.APPROVED_FOR_RISK
    assert candidate.symbol == "EUR_USD"


def test_commentary_signal_is_observe_only():
    signal = ParsedSignal(
        raw_message_id="raw-1",
        source="telegram_test",
        status=ParsedSignalStatus.COMMENTARY_ONLY,
        reason="No symbol or action found",
    )

    candidate = DecisionEngine().evaluate(signal)

    assert candidate.status == TradeCandidateStatus.OBSERVE_ONLY
    assert candidate.reason == "No symbol or action found"


def test_decision_module_does_not_import_execution():
    source = inspect.getsource(decision_engine)

    assert "execution" not in source
