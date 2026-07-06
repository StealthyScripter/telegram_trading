from dataclasses import FrozenInstanceError

import pytest

from decision.channel_intelligence import ChannelGrade, ChannelProfileStore
from tests.unit.decision.channel_intelligence.helpers import service


def test_profile_creation_persists(tmp_path):
    intelligence = service(tmp_path)

    profile = intelligence.get_or_create_profile("telegram_alpha")
    reloaded = ChannelProfileStore(path=str(tmp_path / "profiles.json")).get(
        "telegram_alpha"
    )

    assert reloaded is not None
    assert reloaded.id == profile.id
    assert reloaded.grade == ChannelGrade.UNKNOWN


def test_channel_profile_is_immutable(tmp_path):
    profile = service(tmp_path).get_or_create_profile("telegram_alpha")

    with pytest.raises(FrozenInstanceError):
        profile.score = 99


def test_empty_history_evaluates_as_unknown_or_observe(tmp_path):
    intelligence = service(tmp_path)

    context = intelligence.evaluate_source("empty_source")

    assert context.channel_score == 0
    assert context.grade in {ChannelGrade.UNKNOWN, ChannelGrade.OBSERVE}
    assert context.live_enabled is False
