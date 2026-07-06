import inspect

from contracts.parsed_signal import ParsedSignal, ParsedSignalStatus
from contracts.trade_candidate import TradeCandidateStatus
from decision.channel_intelligence import (
    ApprovalState,
    ChannelGrade,
    DecisionContext,
    ManualOverride,
    PromotionAction,
    PromotionDecision,
)
from decision import decision_engine
from decision.decision_engine import DecisionConfig, DecisionEngine, DecisionEventType, DecisionOutcomeStatus
from decision.ensemble import ConsensusScore, EnsembleDecision
from decision.ml_model import MLModel, ModelDecisionContext
from decision.strategy_fusion import FusionDecision
from events.ledger import EventLedger


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


class FakeChannelIntelligence:
    def __init__(self, score=100, grade=ChannelGrade.LIVE):
        self.score = score
        self.grade = grade

    def record_parsed_signal(self, parsed_signal):
        self.recorded = parsed_signal.id

    def evaluate_source(self, source):
        return DecisionContext(
            source_name=source,
            channel_score=self.score,
            grade=self.grade,
            approval_state=ApprovalState.AUTOMATIC,
            manual_override=ManualOverride.NONE,
            paper_enabled=True,
            live_enabled=True,
            promotion_decision=PromotionDecision(
                action=PromotionAction.PROMOTE,
                grade=self.grade,
                reason="channel ok",
            ),
            approval_reason="channel ok",
        )


def test_valid_signal_creates_trade_candidate(tmp_path):
    candidate = DecisionEngine(
        ledger=EventLedger(path=str(tmp_path / "decision.json"))
    ).evaluate(make_signal())

    assert candidate.status == TradeCandidateStatus.APPROVED_FOR_RISK
    assert candidate.symbol == "EUR_USD"


def test_commentary_signal_is_observe_only(tmp_path):
    signal = ParsedSignal(
        raw_message_id="raw-1",
        source="telegram_test",
        status=ParsedSignalStatus.COMMENTARY_ONLY,
        reason="No symbol or action found",
    )

    candidate = DecisionEngine(
        ledger=EventLedger(path=str(tmp_path / "decision.json"))
    ).evaluate(signal)

    assert candidate.status == TradeCandidateStatus.OBSERVE_ONLY
    assert candidate.reason == "No symbol or action found"


def test_decision_module_does_not_import_execution():
    source = inspect.getsource(decision_engine)

    assert "execution" not in source


def test_evaluate_decision_approves_strong_valid_signal(tmp_path):
    ledger = EventLedger(path=str(tmp_path / "decision.json"))
    outcome = DecisionEngine(ledger=ledger).evaluate_decision(make_signal())

    assert outcome.status == DecisionOutcomeStatus.APPROVE
    assert outcome.candidate.status == TradeCandidateStatus.APPROVED_FOR_RISK
    assert outcome.rationale.contributions[0].name == "parsed_signal"


def test_evaluate_decision_rejects_weak_invalid_signal(tmp_path):
    signal = make_signal(ParsedSignalStatus.INVALID_SIGNAL)

    outcome = DecisionEngine(ledger=EventLedger(path=str(tmp_path / "decision.json"))).evaluate_decision(signal)

    assert outcome.status == DecisionOutcomeStatus.HOLD
    assert outcome.candidate.status == TradeCandidateStatus.OBSERVE_ONLY


def test_evaluate_decision_produces_hold_outcome(tmp_path):
    engine = DecisionEngine(
        config=DecisionConfig(approve_threshold=0.9, reject_threshold=0.1),
        ledger=EventLedger(path=str(tmp_path / "decision.json")),
    )

    outcome = engine.evaluate_decision(make_signal())

    assert outcome.status == DecisionOutcomeStatus.HOLD
    assert outcome.candidate.status == TradeCandidateStatus.OBSERVE_ONLY
    assert "Decision held" in outcome.candidate.reason


def test_same_inputs_produce_same_decision_score(tmp_path):
    engine = DecisionEngine(ledger=EventLedger(path=str(tmp_path / "decision.json")))

    first = engine.evaluate_decision(make_signal())
    second = engine.evaluate_decision(make_signal())

    assert first.status == second.status
    assert first.score == second.score
    assert first.rationale.contributions == second.rationale.contributions


def test_ensemble_contribution_breakdown_is_deterministic(tmp_path):
    ensemble = EnsembleDecision(
        approved=True,
        reason="ensemble ok",
        consensus_score=ConsensusScore(
            symbol="EUR_USD",
            action="buy",
            score=0.8,
            total_weight=2.0,
            source_count=2,
        ),
    )

    outcome = DecisionEngine(ledger=EventLedger(path=str(tmp_path / "decision.json"))).evaluate_decision(
        make_signal(),
        ensemble_decision=ensemble,
    )

    contribution = next(item for item in outcome.rationale.contributions if item.name == "ensemble")
    assert contribution.score == 0.8
    assert contribution.value == 0.12


def test_channel_intelligence_affects_decision_score(tmp_path):
    engine = DecisionEngine(
        channel_intelligence=FakeChannelIntelligence(score=50),
        ledger=EventLedger(path=str(tmp_path / "decision.json")),
    )

    outcome = engine.evaluate_decision(make_signal())

    contribution = next(item for item in outcome.rationale.contributions if item.name == "channel_intelligence")
    assert contribution.score == 0.5
    assert contribution.value == 0.1


def test_strategy_fusion_affects_decision_score(tmp_path):
    fusion = FusionDecision(
        approved=True,
        reason="fusion ok",
        candidate=None,
    )

    outcome = DecisionEngine(ledger=EventLedger(path=str(tmp_path / "decision.json"))).evaluate_decision(
        make_signal(),
        fusion_decision=fusion,
    )

    contribution = next(item for item in outcome.rationale.contributions if item.name == "strategy_fusion")
    assert contribution.score == 1.0
    assert contribution.value == 0.1


def test_ml_advisory_affects_score_only(tmp_path):
    signal = make_signal()
    prediction = MLModel(ledger=EventLedger(path=str(tmp_path / "ml.json"))).score(
        signal,
        ModelDecisionContext(source_score=100),
    )

    outcome = DecisionEngine(ledger=EventLedger(path=str(tmp_path / "decision.json"))).evaluate_decision(
        signal,
        ml_prediction=prediction,
    )

    contribution = next(item for item in outcome.rationale.contributions if item.name == "ml_advisory")
    assert contribution.score == prediction.score
    assert contribution.value <= 0.05


def test_ml_advisory_cannot_directly_approve_invalid_signal(tmp_path):
    signal = make_signal(ParsedSignalStatus.INVALID_SIGNAL)
    prediction = MLModel(ledger=EventLedger(path=str(tmp_path / "ml.json"))).score(
        make_signal(),
        ModelDecisionContext(source_score=100),
    )

    outcome = DecisionEngine(ledger=EventLedger(path=str(tmp_path / "decision.json"))).evaluate_decision(
        signal,
        ml_prediction=prediction,
    )

    assert outcome.status == DecisionOutcomeStatus.HOLD
    assert outcome.candidate.status == TradeCandidateStatus.OBSERVE_ONLY


def test_decision_created_event_emitted(tmp_path):
    ledger = EventLedger(path=str(tmp_path / "decision.json"))

    outcome = DecisionEngine(ledger=ledger).evaluate_decision(make_signal())

    event = ledger.latest(1)[0]
    assert event["payload"]["event_type"] == DecisionEventType.DECISION_CREATED.value
    assert event["payload"]["trade_candidate_id"] == outcome.candidate.id
    assert event["payload"]["score"] == outcome.score
