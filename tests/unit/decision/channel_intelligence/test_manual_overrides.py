from decision.channel_intelligence import ChannelGrade, ManualOverride
from tests.unit.decision.channel_intelligence.helpers import service


def test_force_observe_override(tmp_path):
    profile = service(tmp_path).set_manual_override(
        "telegram_alpha",
        ManualOverride.FORCE_OBSERVE,
        reason="manual safety review",
    )

    assert profile.grade == ChannelGrade.OBSERVE
    assert profile.live_enabled is False
    assert profile.approval_reason == "manual safety review"


def test_force_paper_override(tmp_path):
    profile = service(tmp_path).set_manual_override(
        "telegram_alpha",
        ManualOverride.FORCE_PAPER,
    )

    assert profile.grade == ChannelGrade.PAPER
    assert profile.paper_enabled is True
    assert profile.live_enabled is False


def test_force_live_override(tmp_path):
    profile = service(tmp_path).set_manual_override(
        "telegram_alpha",
        ManualOverride.FORCE_LIVE,
    )

    assert profile.grade == ChannelGrade.LIVE
    assert profile.paper_enabled is True
    assert profile.live_enabled is True


def test_force_reject_override(tmp_path):
    profile = service(tmp_path).set_manual_override(
        "telegram_alpha",
        ManualOverride.FORCE_REJECT,
    )

    assert profile.grade == ChannelGrade.REJECTED
    assert profile.paper_enabled is False
    assert profile.live_enabled is False
