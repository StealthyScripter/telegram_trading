from contracts.parsed_signal import ParsedSignalStatus
from decision.channel_intelligence import ChannelIntelligence
from tests.unit.decision.channel_intelligence.helpers import (
    parsed_signal,
    service,
    make_test_config,
    trade_result,
)


class InMemoryProfileStore:
    def __init__(self):
        self.profiles = {}

    def get(self, source_name):
        return self.profiles.get(source_name)

    def save(self, profile):
        self.profiles[profile.source_name] = profile
        return profile

    def all_profiles(self):
        return list(self.profiles.values())


class NoopLedger:
    def append(self, event):
        return event.to_dict()


def test_parsed_signal_metrics_update_incrementally(tmp_path):
    intelligence = service(tmp_path)

    intelligence.record_parsed_signal(parsed_signal())
    profile = intelligence.record_parsed_signal(
        parsed_signal(status=ParsedSignalStatus.COMMENTARY_ONLY)
    )

    stats = profile.rolling_statistics
    assert stats.signals_received == 2
    assert stats.parsed_signals == 2
    assert stats.valid_signals == 1


def test_trade_metrics_update_incrementally(tmp_path):
    intelligence = service(tmp_path)

    intelligence.record_trade_result("telegram_alpha", trade_result(2))
    profile = intelligence.record_trade_result("telegram_alpha", trade_result(-1))

    stats = profile.rolling_statistics
    assert stats.closed_trades == 2
    assert stats.wins == 1
    assert stats.losses == 1
    assert stats.win_rate == 0.5
    assert stats.expectancy == 0.5
    assert stats.profit_factor == 2
    assert stats.daily_returns
    assert stats.average_hold_time > 0


def test_thousands_of_trades_increment_without_replay(tmp_path):
    intelligence = ChannelIntelligence(
        store=InMemoryProfileStore(),
        ledger=NoopLedger(),
        config=make_test_config(),
    )

    for index in range(1000):
        intelligence.record_trade_result(
            "telegram_bulk",
            trade_result(1 if index % 2 == 0 else -0.5),
        )

    profile = intelligence.store.get("telegram_bulk")

    assert profile.rolling_statistics.closed_trades == 1000
    assert profile.rolling_statistics.wins == 500
    assert profile.rolling_statistics.losses == 500
    assert profile.rolling_statistics.expectancy == 0.25
