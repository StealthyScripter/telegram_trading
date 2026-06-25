import os


class AccountRouter:
    def __init__(self):
        self.accounts = {
            "oanda": {
                "default": os.getenv("OANDA_DEFAULT_ACCOUNT") or os.getenv("OANDA_ACCOUNT_ID"),
                "scalping": os.getenv("OANDA_ACCOUNT_SCALPING"),
                "day_trading": os.getenv("OANDA_ACCOUNT_DAY_TRADING"),
                "long_term": os.getenv("OANDA_ACCOUNT_LONG_TERM"),
                "signals": os.getenv("OANDA_ACCOUNT_SIGNALS"),
            }
        }

    def resolve_account_id(
        self,
        broker_name: str,
        strategy_account: str | None = None,
        explicit_account_id: str | None = None,
    ) -> str:
        if explicit_account_id:
            return explicit_account_id

        broker_accounts = self.accounts.get(broker_name)

        if not broker_accounts:
            raise ValueError(f"No accounts configured for broker: {broker_name}")

        key = strategy_account or "default"
        account_id = broker_accounts.get(key)

        if not account_id:
            raise ValueError(
                f"No {broker_name} account configured for route: {key}"
            )

        return account_id
