from signals.signal_parser import SignalParser, SignalParseStatus


def test_parse_valid_buy_signal():
    parser = SignalParser()

    result = parser.parse("BUY EURUSD @ 1.1370 SL 1.1340 TP 1.1400")

    assert result.status == SignalParseStatus.VALID_SIGNAL
    assert result.symbol == "EUR_USD"
    assert result.action == "buy"
    assert result.entry_price == "1.1370"
    assert result.stop_loss == "1.1340"
    assert result.take_profits == ["1.1400"]


def test_parse_valid_sell_signal_with_multiple_tps():
    parser = SignalParser()

    result = parser.parse(
        "SELL GBPUSD ENTRY 1.2700 SL 1.2750 TP1 1.2650 TP2 1.2600"
    )

    assert result.status == SignalParseStatus.VALID_SIGNAL
    assert result.symbol == "GBP_USD"
    assert result.action == "sell"
    assert result.entry_price == "1.2700"
    assert result.stop_loss == "1.2750"
    assert result.take_profits == ["1.2650", "1.2600"]


def test_parse_gold_alias():
    parser = SignalParser()

    result = parser.parse("BUY GOLD SL 2300 TP 2350")

    assert result.symbol == "XAU_USD"
    assert result.action == "buy"


def test_parse_market_signal_without_entry():
    parser = SignalParser()

    result = parser.parse("BUY NOW EURUSD SL 1.1300 TP 1.1400")

    assert result.status == SignalParseStatus.VALID_SIGNAL
    assert result.entry_type == "market"
    assert result.entry_price is None


def test_partial_signal_missing_tp_and_sl():
    parser = SignalParser()

    result = parser.parse("BUY EURUSD now")

    assert result.status == SignalParseStatus.PARTIAL_SIGNAL
    assert "stop_loss" in result.reason
    assert "take_profit" in result.reason


def test_commentary_only_message():
    parser = SignalParser()

    result = parser.parse("London session is looking volatile today")

    assert result.status == SignalParseStatus.COMMENTARY_ONLY


def test_close_signal():
    parser = SignalParser()

    result = parser.parse("Close trade now EURUSD")

    assert result.status == SignalParseStatus.CLOSE_SIGNAL


def test_update_signal():
    parser = SignalParser()

    result = parser.parse("Move SL to BE on EURUSD")

    assert result.status == SignalParseStatus.UPDATE_SIGNAL


def test_invalid_empty_message():
    parser = SignalParser()

    result = parser.parse("   ")

    assert result.status == SignalParseStatus.INVALID_SIGNAL


def test_to_dict():
    parser = SignalParser()

    result = parser.parse("BUY EURUSD SL 1.1300 TP 1.1400")
    data = result.to_dict()

    assert data["status"] == "VALID_SIGNAL"
    assert data["symbol"] == "EUR_USD"

