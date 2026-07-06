from decision.channel_intelligence import ChannelEventType
from tests.unit.decision.channel_intelligence.helpers import service, trade_result


def test_channel_events_are_emitted(tmp_path):
    intelligence = service(tmp_path)

    intelligence.record_trade_result("telegram_alpha", trade_result(1))

    event_types = [
        event["payload"]["event_type"]
        for event in intelligence.ledger.all_events()
    ]

    assert ChannelEventType.CHANNEL_CREATED.value in event_types
    assert ChannelEventType.CHANNEL_METRICS_UPDATED.value in event_types
    assert ChannelEventType.CHANNEL_SCORE_UPDATED.value in event_types
