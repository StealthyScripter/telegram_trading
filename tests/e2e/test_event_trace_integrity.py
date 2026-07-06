from tests.e2e.helpers import run_full_paper_flow


def test_event_trace_can_reconstruct_major_path(tmp_path):
    result = run_full_paper_flow(tmp_path)
    events = result["ledger"].all_events()
    stages = [event["stage"] for event in events]

    for expected_stage in [
        "parsing",
        "decision",
        "ensemble",
        "ml_signal_quality",
        "portfolio_risk",
        "capital_allocation",
        "execution",
        "learning",
    ]:
        assert expected_stage in stages

    by_output = {
        event.get("output_id"): event
        for event in events
        if event.get("output_id")
    }

    assert result["parsed_signal"].id in by_output
    assert result["trade_candidate"].id in by_output
    assert result["risk_decision"].id in by_output
    assert result["allocation"].id in by_output
    assert result["execution_result"].id in by_output

    assert result["execution_request"].capital_allocation_id == result["allocation"].id
    assert result["allocation"].risk_decision_id == result["risk_decision"].id
    assert result["risk_decision"].trade_candidate_id == result["ensemble_decision"].candidate.id
