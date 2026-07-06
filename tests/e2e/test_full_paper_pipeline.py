from contracts.execution_result import ContractExecutionStatus
from contracts.risk_decision import RiskDecisionStatus
from contracts.trade_candidate import TradeCandidateStatus
from tests.e2e.helpers import run_full_paper_flow


def test_full_safe_paper_pipeline(tmp_path):
    result = run_full_paper_flow(tmp_path)

    assert result["raw_message"].id
    assert result["parsed_signal"].id
    assert result["trade_candidate"].id
    assert result["ensemble_decision"].ensemble.id
    assert result["ml_prediction"].model_version.identifier
    assert result["risk_decision"].status == RiskDecisionStatus.APPROVED
    assert result["allocation"].id
    assert result["execution_request"].id
    assert result["execution_result"].id
    assert result["execution_result"].status == ContractExecutionStatus.FILLED
    assert result["execution_result"].broker == "paper"
    assert result["recommendation"].id

    assert result["trade_candidate"].status == TradeCandidateStatus.APPROVED_FOR_RISK
    assert result["ensemble_decision"].approved is True
    assert result["ml_prediction"].approved is True
