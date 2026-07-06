from ingestion.manual import ManualSignalIngestor


def test_manual_signal_to_raw_message():
    message = ManualSignalIngestor().ingest(
        raw_text="BUY EURUSD SL 1.0950 TP 1.1100",
        source="manual_desk",
        message_id="manual-1",
    )

    assert message.source == "manual_desk"
    assert message.source_type == "manual"
    assert message.message_id == "manual-1"
    assert message.raw_text == "BUY EURUSD SL 1.0950 TP 1.1100"
