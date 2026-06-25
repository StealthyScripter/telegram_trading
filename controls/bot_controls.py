import os


class BotControls:
    def kill_switch_enabled(self) -> bool:
        return os.getenv("BOT_KILL_SWITCH", "false").lower() == "true"

    def live_trading_allowed(self) -> bool:
        return os.getenv("ALLOW_LIVE_TRADING", "false").lower() == "true"

    def assert_can_trade(self, broker_env: str):
        if self.kill_switch_enabled():
            raise RuntimeError(
                "BOT_KILL_SWITCH is enabled. No new trades or closes are allowed."
            )

        if broker_env == "live" and not self.live_trading_allowed():
            raise RuntimeError(
                "Live trading blocked. Set ALLOW_LIVE_TRADING=true to permit live orders."
            )
