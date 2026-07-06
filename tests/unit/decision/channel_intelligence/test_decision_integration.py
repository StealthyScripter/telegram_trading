from contracts.trade_candidate import TradeCandidateStatus
from decision.channel_intelligence import ManualOverride
from decision.decision_engine import DecisionEngine
from tests.unit.decision.channel_intelligence.helpers import parsed_signal, service


def test_decision_engine_consumes_channel_context(tmp_path):
    intelligence = service(tmp_path)
    intelligence.set_manual_override("telegram_test", ManualOverride.FORCE_PAPER)

    candidate = DecisionEngine(channel_intelligence=intelligence).evaluate(
        parsed_signal()
    )

    assert candidate.status == TradeCandidateStatus.PAPER_ONLY
    assert "Manual override" in candidate.reason


def test_decision_engine_force_reject_does_not_execute_or_approve(tmp_path):
    intelligence = service(tmp_path)
    intelligence.set_manual_override("telegram_test", ManualOverride.FORCE_REJECT)

    candidate = DecisionEngine(channel_intelligence=intelligence).evaluate(
        parsed_signal()
    )

    assert candidate.status == TradeCandidateStatus.REJECTED
