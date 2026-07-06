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
    enable_confidence_weighting: bool = False
    minimum_confidence_multiplier: float = 0.25
    enable_strategy_weighting: bool = False
    strategy_weight_rules: dict[str, float] = field(default_factory=dict)
    default_strategy_multiplier: float = 1.0
    enable_volatility_adjustment: bool = False
    target_volatility: float = 1.0
    minimum_volatility_multiplier: float = 0.25
    maximum_volatility_multiplier: float = 1.0
    enable_portfolio_risk_adjustment: bool = False
    portfolio_risk_multiplier: float = 1.0
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

        if not 0 <= self.minimum_confidence_multiplier <= 1:
            raise ValueError("AllocationConfig.minimum_confidence_multiplier must be between 0 and 1")

        if self.default_strategy_multiplier < 0:
            raise ValueError("AllocationConfig.default_strategy_multiplier cannot be negative")

        for name, multiplier in self.strategy_weight_rules.items():
            if not name:
                raise ValueError("AllocationConfig.strategy_weight_rules keys cannot be empty")
            if multiplier < 0:
                raise ValueError("AllocationConfig.strategy_weight_rules multipliers cannot be negative")

        if self.target_volatility <= 0:
            raise ValueError("AllocationConfig.target_volatility must be greater than 0")

        if self.minimum_volatility_multiplier < 0:
            raise ValueError("AllocationConfig.minimum_volatility_multiplier cannot be negative")

        if self.maximum_volatility_multiplier <= 0:
            raise ValueError("AllocationConfig.maximum_volatility_multiplier must be greater than 0")

        if self.minimum_volatility_multiplier > self.maximum_volatility_multiplier:
            raise ValueError("AllocationConfig.minimum_volatility_multiplier cannot exceed maximum")

        if self.portfolio_risk_multiplier < 0:
            raise ValueError("AllocationConfig.portfolio_risk_multiplier cannot be negative")

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
            enable_confidence_weighting=data.get("enable_confidence_weighting", defaults.enable_confidence_weighting),
            minimum_confidence_multiplier=data.get(
                "minimum_confidence_multiplier",
                defaults.minimum_confidence_multiplier,
            ),
            enable_strategy_weighting=data.get("enable_strategy_weighting", defaults.enable_strategy_weighting),
            strategy_weight_rules=data.get("strategy_weight_rules", defaults.strategy_weight_rules),
            default_strategy_multiplier=data.get(
                "default_strategy_multiplier",
                defaults.default_strategy_multiplier,
            ),
            enable_volatility_adjustment=data.get(
                "enable_volatility_adjustment",
                defaults.enable_volatility_adjustment,
            ),
            target_volatility=data.get("target_volatility", defaults.target_volatility),
            minimum_volatility_multiplier=data.get(
                "minimum_volatility_multiplier",
                defaults.minimum_volatility_multiplier,
            ),
            maximum_volatility_multiplier=data.get(
                "maximum_volatility_multiplier",
                defaults.maximum_volatility_multiplier,
            ),
            enable_portfolio_risk_adjustment=data.get(
                "enable_portfolio_risk_adjustment",
                defaults.enable_portfolio_risk_adjustment,
            ),
            portfolio_risk_multiplier=data.get("portfolio_risk_multiplier", defaults.portfolio_risk_multiplier),
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
    explanation: dict = field(default_factory=dict)
