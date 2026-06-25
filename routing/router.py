import json
import os
from pathlib import Path


class DynamicOrderRouter:
    def __init__(self, config_path: str = "routing/routing_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        with self.config_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def resolve_route(
        self,
        source: str | None = None,
        broker: str | None = None,
        strategy_account: str | None = None,
        explicit_account_id: str | None = None,
    ) -> dict:
        if explicit_account_id:
            return {
                "broker": broker or self.config["default_broker"],
                "strategy_account": strategy_account,
                "account_id": explicit_account_id,
                "route_reason": "explicit_account_id",
            }

        source_route = self.config.get("source_routes", {}).get(source)

        resolved_broker = (
            broker
            or (source_route or {}).get("broker")
            or self.config["default_broker"]
        )

        resolved_strategy_account = (
            strategy_account
            or (source_route or {}).get("strategy_account")
        )

        account_id = self._resolve_account_id(
            broker=resolved_broker,
            strategy_account=resolved_strategy_account,
        )

        return {
            "broker": resolved_broker,
            "strategy_account": resolved_strategy_account,
            "account_id": account_id,
            "route_reason": "source_route" if source_route else "default_route",
        }

    def _resolve_account_id(self, broker: str, strategy_account: str | None):
        broker_config = self.config["brokers"].get(broker)

        if not broker_config:
            raise ValueError(f"No routing config found for broker: {broker}")

        if strategy_account:
            account_config = broker_config["accounts"].get(strategy_account)

            if not account_config:
                raise ValueError(
                    f"No routing account found for {broker}.{strategy_account}"
                )

            account_env = account_config["account_env"]
            account_id = os.getenv(account_env)

            if not account_id:
                raise ValueError(f"Missing env variable for account: {account_env}")

            return account_id

        default_env = broker_config["default_account_env"]
        account_id = os.getenv(default_env) or os.getenv("OANDA_ACCOUNT_ID")

        if not account_id:
            raise ValueError(f"Missing default account env: {default_env}")

        return account_id
