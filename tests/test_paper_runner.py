from paper_trading.paper_runner import PaperRunner
from paper_trading.paper_store import PaperTradeStore


def test_paper_runner_creates_trade(tmp_path):
    runner = PaperRunner()
    runner.store = PaperTradeStore(path=str(tmp_path / "paper.json"))

    signal = {
        "signal_id": "telegram:1",
        "source": "telegram_test",
        "execution_status": "READY_FOR_PAPER",
        "parsed_signal": {
            "symbol": "EUR_USD",
            "action": "buy",
            "entry_price": None,
            "stop_loss": "1.1300",
            "take_profits": ["1.1400"],
        },
    }

    result = runner.paper_trade_signal(signal)

    assert result["created"] is True
    assert result["paper_trade"]["symbol"] == "EUR_USD"


def test_paper_runner_rejects_unready_signal(tmp_path):
    runner = PaperRunner()
    runner.store = PaperTradeStore(path=str(tmp_path / "paper.json"))

    signal = {
        "signal_id": "telegram:1",
        "source": "telegram_test",
        "execution_status": "OBSERVE_ONLY",
        "parsed_signal": {},
    }

    result = runner.paper_trade_signal(signal)

    assert result["created"] is False
