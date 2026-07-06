from tests.e2e.helpers import run_full_paper_flow


def test_e2e_does_not_touch_live_broker(monkeypatch, tmp_path):
    touched = {"live": False}

    def fail_live_create(*args, **kwargs):
        touched["live"] = True
        raise AssertionError("Live broker path must not be touched in safe E2E tests")

    monkeypatch.setattr("brokers.factory.BrokerFactory.create", fail_live_create)
    monkeypatch.setattr("brokers.oanda.OandaBroker.__init__", fail_live_create)

    result = run_full_paper_flow(tmp_path)

    assert result["execution_result"].broker == "paper"
    assert touched["live"] is False
