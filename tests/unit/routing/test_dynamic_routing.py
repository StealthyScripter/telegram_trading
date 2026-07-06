import json

from routing.router import DynamicOrderRouter


def test_source_routes_to_configured_account(monkeypatch, tmp_path):
    config = {
        "default_broker": "oanda",
        "brokers": {
            "oanda": {
                "default_account_env": "OANDA_DEFAULT_ACCOUNT",
                "accounts": {
                    "scalping": {
                        "account_env": "OANDA_ACCOUNT_SCALPING",
                        "description": "Scalping"
                    }
                }
            }
        },
        "source_routes": {
            "telegram_scalping": {
                "broker": "oanda",
                "strategy_account": "scalping"
            }
        }
    }

    path = tmp_path / "routing_config.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    monkeypatch.setenv("OANDA_ACCOUNT_SCALPING", "acct-scalping")

    router = DynamicOrderRouter(config_path=str(path))

    route = router.resolve_route(source="telegram_scalping")

    assert route["broker"] == "oanda"
    assert route["strategy_account"] == "scalping"
    assert route["account_id"] == "acct-scalping"
    assert route["route_reason"] == "source_route"


def test_explicit_account_overrides_source_route(monkeypatch, tmp_path):
    config = {
        "default_broker": "oanda",
        "brokers": {
            "oanda": {
                "default_account_env": "OANDA_DEFAULT_ACCOUNT",
                "accounts": {}
            }
        },
        "source_routes": {}
    }

    path = tmp_path / "routing_config.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    router = DynamicOrderRouter(config_path=str(path))

    route = router.resolve_route(
        source="anything",
        broker="oanda",
        explicit_account_id="explicit-account",
    )

    assert route["account_id"] == "explicit-account"
    assert route["route_reason"] == "explicit_account_id"


def test_default_account_used_when_no_source(monkeypatch, tmp_path):
    config = {
        "default_broker": "oanda",
        "brokers": {
            "oanda": {
                "default_account_env": "OANDA_DEFAULT_ACCOUNT",
                "accounts": {}
            }
        },
        "source_routes": {}
    }

    path = tmp_path / "routing_config.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    monkeypatch.setenv("OANDA_DEFAULT_ACCOUNT", "acct-default")

    router = DynamicOrderRouter(config_path=str(path))

    route = router.resolve_route()

    assert route["broker"] == "oanda"
    assert route["account_id"] == "acct-default"
    assert route["route_reason"] == "default_route"
