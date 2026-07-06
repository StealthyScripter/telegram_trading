from contracts.raw_message import RawMessage
from contracts.risk_decision import RiskDecisionStatus
from events.ledger import EventLedger
from orchestration.pipeline import Pipeline
from risk.portfolio import PortfolioState, RiskPolicy
from risk.risk_engine import RiskEngine


def raw_message():
    return RawMessage(
        source="alpha",
        message_id="1",
        posted_at="2026-01-01T10:00:00+00:00",
        received_at="2026-01-01T10:00:01+00:00",
        raw_text="BUY EURUSD SL 1.0950 TP 1.1100",
    )


def test_risk_pipeline_approves_candidate(tmp_path):
    pipeline = Pipeline(ledger=EventLedger(path=str(tmp_path / "pipeline.json")))
    result = pipeline.run(raw_message())
    risk = RiskEngine(ledger=EventLedger(path=str(tmp_path / "risk.json")))

    decision = risk.evaluate(
        result.trade_candidate,
        PortfolioState(account_id="acct-1", broker="oanda", equity=10000),
    )

    assert decision.status == RiskDecisionStatus.APPROVED
    assert risk.ledger.find_by_stage("portfolio_risk")


def test_risk_pipeline_rejects_by_policy(tmp_path):
    pipeline = Pipeline(ledger=EventLedger(path=str(tmp_path / "pipeline.json")))
    result = pipeline.run(raw_message())
    risk = RiskEngine(
        policy=RiskPolicy(max_daily_risk=0),
        ledger=EventLedger(path=str(tmp_path / "risk.json")),
    )

    decision = risk.evaluate(
        result.trade_candidate,
        PortfolioState(
            account_id="acct-1",
            broker="oanda",
            equity=10000,
            daily_risk_used=0,
        ),
    )

    assert decision.status == RiskDecisionStatus.REJECTED
