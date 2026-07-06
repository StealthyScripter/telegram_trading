import json

from decision.channel_intelligence import ChannelIntelligenceConfig


def test_configuration_loads_from_dict():
    config = ChannelIntelligenceConfig.from_dict(
        {
            "thresholds": {"minimum_signals": 5},
            "weights": {"expectancy": 0.4},
            "version": "2",
        }
    )

    assert config.thresholds.minimum_signals == 5
    assert config.weights.expectancy == 0.4
    assert config.version == "2"


def test_configuration_loads_from_path(tmp_path):
    path = tmp_path / "channel_config.json"
    path.write_text(
        json.dumps({"thresholds": {"minimum_win_rate": 0.6}}),
        encoding="utf-8",
    )

    config = ChannelIntelligenceConfig.from_path(str(path))

    assert config.thresholds.minimum_win_rate == 0.6
