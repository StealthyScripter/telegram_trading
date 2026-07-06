import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class AccountMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


@dataclass(frozen=True)
class AccountCapitalState:
    account_id: str
    broker: str
    balance: float
    equity: float
    available_margin: float
    currency: str = "USD"
    mode: AccountMode = AccountMode.PAPER

    def __post_init__(self):
        if not self.account_id:
            raise ValueError("AccountCapitalState.account_id is required")

        if not self.broker:
            raise ValueError("AccountCapitalState.broker is required")

        if self.equity <= 0:
            raise ValueError("AccountCapitalState.equity must be greater than 0")

        if self.balance < 0:
            raise ValueError("AccountCapitalState.balance cannot be negative")

        if self.available_margin < 0:
            raise ValueError("AccountCapitalState.available_margin cannot be negative")


@dataclass(frozen=True)
class ChannelWeightRule:
    minimum_score: float
    multiplier: float

    def __post_init__(self):
        if not 0 <= self.minimum_score <= 100:
            raise ValueError("ChannelWeightRule.minimum_score must be between 0 and 100")

        if self.multiplier < 0:
            raise ValueError("ChannelWeightRule.multiplier cannot be negative")


@dataclass(frozen=True)
class AllocationConfig:
    base_risk_percent: float = 0.01
    min_risk_percent: float = 0.001
    max_risk_percent: float = 0.02
    paper_multiplier: float = 1.0
    live_multiplier: float = 1.0
    min_units: int = 1
    max_units: int = 1000
    maximum_position_value: float | None = None
    minimum_channel_score: float = 0.0
    enable_channel_weighting: bool = True
    channel_weight_rules: tuple[ChannelWeightRule, ...] = field(
        default_factory=lambda: (
            ChannelWeightRule(minimum_score=90, multiplier=1.0),
            ChannelWeightRule(minimum_score=80, multiplier=0.75),
            ChannelWeightRule(minimum_score=70, multiplier=0.5),
            ChannelWeightRule(minimum_score=0, multiplier=0.25),
        )
    )

    def __post_init__(self):
        if self.base_risk_percent <= 0:
            raise ValueError("AllocationConfig.base_risk_percent must be greater than 0")

        if self.min_risk_percent < 0:
            raise ValueError("AllocationConfig.min_risk_percent cannot be negative")

        if self.max_risk_percent <= 0:
            raise ValueError("AllocationConfig.max_risk_percent must be greater than 0")

        if self.min_risk_percent > self.max_risk_percent:
            raise ValueError("AllocationConfig.min_risk_percent cannot exceed max_risk_percent")

        if self.min_units <= 0:
            raise ValueError("AllocationConfig.min_units must be greater than 0")

        if self.max_units < self.min_units:
            raise ValueError("AllocationConfig.max_units cannot be less than min_units")

        if self.paper_multiplier < 0 or self.live_multiplier < 0:
            raise ValueError("AllocationConfig multipliers cannot be negative")

        if not 0 <= self.minimum_channel_score <= 100:
            raise ValueError("AllocationConfig.minimum_channel_score must be between 0 and 100")

    @classmethod
    def from_dict(cls, data: dict | None):
        data = data or {}
        defaults = cls()
        rules = data.get("channel_weight_rules")
        parsed_rules = (
            tuple(ChannelWeightRule(**rule) for rule in rules)
            if rules is not None
            else defaults.channel_weight_rules
        )
        return cls(
            base_risk_percent=data.get("base_risk_percent", defaults.base_risk_percent),
            min_risk_percent=data.get("min_risk_percent", defaults.min_risk_percent),
            max_risk_percent=data.get("max_risk_percent", defaults.max_risk_percent),
            paper_multiplier=data.get("paper_multiplier", defaults.paper_multiplier),
            live_multiplier=data.get("live_multiplier", defaults.live_multiplier),
            min_units=data.get("min_units", defaults.min_units),
            max_units=data.get("max_units", defaults.max_units),
            maximum_position_value=data.get("maximum_position_value"),
            minimum_channel_score=data.get("minimum_channel_score", defaults.minimum_channel_score),
            enable_channel_weighting=data.get("enable_channel_weighting", defaults.enable_channel_weighting),
            channel_weight_rules=parsed_rules,
        )

    @classmethod
    def from_path(cls, path: str):
        with Path(path).open("r", encoding="utf-8") as file:
            return cls.from_dict(json.load(file))


@dataclass(frozen=True)
class AllocationDecision:
    approved: bool
    reason: str
    risk_amount: float = 0.0
    risk_percent: float = 0.0
    calculated_units: int = 0
    clamped_units: int = 0
