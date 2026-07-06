import json
import os
import tempfile
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4

from contracts.parsed_signal import ParsedSignal, ParsedSignalStatus
from events.ledger import EventLedger
from events.models import DecisionEvent


class ChannelGrade(str, Enum):
    UNKNOWN = "UNKNOWN"
    OBSERVE = "OBSERVE"
    PAPER = "PAPER"
    PROMOTING = "PROMOTING"
    LIVE = "LIVE"
    PAUSED = "PAUSED"
    REJECTED = "REJECTED"
    BLACKLISTED = "BLACKLISTED"


class PromotionAction(str, Enum):
    PROMOTE = "promote"
    HOLD = "hold"
    DEMOTE = "demote"
    PAUSE = "pause"
    REJECT = "reject"


class ManualOverride(str, Enum):
    NONE = "none"
    FORCE_OBSERVE = "force_observe"
    FORCE_PAPER = "force_paper"
    FORCE_LIVE = "force_live"
    FORCE_REJECT = "force_reject"


class ApprovalState(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL_OVERRIDE = "manual_override"


class ChannelEventType(str, Enum):
    CHANNEL_CREATED = "CHANNEL_CREATED"
    CHANNEL_UPDATED = "CHANNEL_UPDATED"
    CHANNEL_PROMOTED = "CHANNEL_PROMOTED"
    CHANNEL_DEMOTED = "CHANNEL_DEMOTED"
    CHANNEL_PAUSED = "CHANNEL_PAUSED"
    CHANNEL_REJECTED = "CHANNEL_REJECTED"
    CHANNEL_SCORE_UPDATED = "CHANNEL_SCORE_UPDATED"
    CHANNEL_METRICS_UPDATED = "CHANNEL_METRICS_UPDATED"


@dataclass(frozen=True)
class PromotionThresholds:
    minimum_signals: int = 30
    minimum_win_rate: float = 0.5
    minimum_expectancy: float = 0.1
    minimum_rr: float = 1.0
    maximum_drawdown: float = 5.0
    maximum_loss_streak: int = 5
    minimum_stability: float = 0.5
    minimum_paper_duration_days: int = 14
    minimum_profit_factor: float = 1.2
    pause_loss_streak: int = 7
    reject_loss_streak: int = 10
    live_score: float = 80.0
    paper_score: float = 55.0
    promoting_score: float = 70.0


@dataclass(frozen=True)
class ScoreWeights:
    expectancy: float = 0.30
    win_rate: float = 0.20
    drawdown: float = 0.20
    consistency: float = 0.15
    profit_factor: float = 0.10
    sample_size: float = 0.05


@dataclass(frozen=True)
class ChannelIntelligenceConfig:
    thresholds: PromotionThresholds = field(default_factory=PromotionThresholds)
    weights: ScoreWeights = field(default_factory=ScoreWeights)
    version: str = "1"

    @classmethod
    def from_dict(cls, data: dict | None):
        data = data or {}
        return cls(
            thresholds=PromotionThresholds(**data.get("thresholds", {})),
            weights=ScoreWeights(**data.get("weights", {})),
            version=str(data.get("version", "1")),
        )

    @classmethod
    def from_path(cls, path: str):
        with Path(path).open("r", encoding="utf-8") as file:
            return cls.from_dict(json.load(file))


@dataclass(frozen=True)
class RollingStatistics:
    signals_received: int = 0
    parsed_signals: int = 0
    valid_signals: int = 0
    executed_paper: int = 0
    executed_live: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0
    average_rr: float = 0.0
    expectancy: float = 0.0
    profit_factor: float | None = None
    win_rate: float = 0.0
    average_hold_time: float = 0.0
    average_stop_distance: float = 0.0
    average_tp_distance: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    consecutive_losses: int = 0
    consecutive_wins: int = 0
    stability_score: float = 0.0
    consistency_score: float = 0.0
    monthly_returns: dict[str, float] = field(default_factory=dict)
    weekly_returns: dict[str, float] = field(default_factory=dict)
    daily_returns: dict[str, float] = field(default_factory=dict)
    gross_win: float = 0.0
    gross_loss: float = 0.0
    total_rr: float = 0.0
    closed_trades: int = 0
    equity_peak: float = 0.0
    cumulative_rr: float = 0.0


@dataclass(frozen=True)
class PromotionDecision:
    action: PromotionAction
    grade: ChannelGrade
    reason: str


@dataclass(frozen=True)
class DecisionContext:
    source_name: str
    channel_score: float
    grade: ChannelGrade
    approval_state: ApprovalState
    manual_override: ManualOverride
    paper_enabled: bool
    live_enabled: bool
    promotion_decision: PromotionDecision
    approval_reason: str


@dataclass(frozen=True)
class ChannelProfile:
    source_name: str
    first_seen: str
    last_seen: str
    status: str = "active"
    score: float = 0.0
    grade: ChannelGrade = ChannelGrade.UNKNOWN
    paper_enabled: bool = False
    live_enabled: bool = False
    manual_override: ManualOverride = ManualOverride.NONE
    approval_state: ApprovalState = ApprovalState.AUTOMATIC
    approval_reason: str | None = None
    rolling_statistics: RollingStatistics = field(default_factory=RollingStatistics)
    version: str = "1"
    id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict:
        data = asdict(self)
        data["grade"] = self.grade.value
        data["manual_override"] = self.manual_override.value
        data["approval_state"] = self.approval_state.value
        return data

    @classmethod
    def from_dict(cls, data: dict):
        stats = data.get("rolling_statistics") or {}
        return cls(
            source_name=data["source_name"],
            first_seen=data["first_seen"],
            last_seen=data["last_seen"],
            status=data.get("status", "active"),
            score=float(data.get("score", 0.0)),
            grade=ChannelGrade(data.get("grade", ChannelGrade.UNKNOWN.value)),
            paper_enabled=bool(data.get("paper_enabled", False)),
            live_enabled=bool(data.get("live_enabled", False)),
            manual_override=ManualOverride(
                data.get("manual_override", ManualOverride.NONE.value)
            ),
            approval_state=ApprovalState(
                data.get("approval_state", ApprovalState.AUTOMATIC.value)
            ),
            approval_reason=data.get("approval_reason"),
            rolling_statistics=RollingStatistics(**stats),
            version=str(data.get("version", "1")),
            id=data.get("id") or str(uuid4()),
        )


class ChannelProfileStore:
    def __init__(self, path: str = "data/channel_profiles.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self._write({"profiles": []})

    def _read(self) -> dict:
        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _write(self, data: dict):
        fd, temp_path = tempfile.mkstemp(
            dir=str(self.path.parent),
            prefix=".channel_profiles_",
            suffix=".json",
        )

        with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
            json.dump(data, temp_file, indent=2, default=str)

        os.replace(temp_path, self.path)

    def all_profiles(self) -> list[ChannelProfile]:
        return [
            ChannelProfile.from_dict(profile)
            for profile in self._read().get("profiles", [])
        ]

    def get(self, source_name: str) -> ChannelProfile | None:
        for profile in self.all_profiles():
            if profile.source_name == source_name:
                return profile
        return None

    def save(self, profile: ChannelProfile):
        data = self._read()
        records = data.setdefault("profiles", [])

        for index, record in enumerate(records):
            if record.get("source_name") == profile.source_name:
                records[index] = profile.to_dict()
                self._write(data)
                return profile

        records.append(profile.to_dict())
        self._write(data)
        return profile


class ChannelScorer:
    def __init__(self, config: ChannelIntelligenceConfig | None = None):
        self.config = config or ChannelIntelligenceConfig()

    def score(self, stats: RollingStatistics) -> float:
        weights = self.config.weights
        thresholds = self.config.thresholds
        sample_size = min(
            stats.closed_trades / thresholds.minimum_signals,
            1.0,
        )
        expectancy_score = self._clamp((stats.expectancy + 1.0) / 2.0)
        drawdown_score = self._clamp(
            1.0 - (stats.max_drawdown / thresholds.maximum_drawdown)
        )
        profit_factor = stats.profit_factor or 0.0
        profit_factor_score = self._clamp(
            profit_factor / thresholds.minimum_profit_factor
        )

        normalized = (
            weights.expectancy * expectancy_score
            + weights.win_rate * self._clamp(stats.win_rate)
            + weights.drawdown * drawdown_score
            + weights.consistency * self._clamp(stats.consistency_score)
            + weights.profit_factor * profit_factor_score
            + weights.sample_size * sample_size
        )

        return round(self._clamp(normalized) * 100, 2)

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))


class ChannelIntelligence:
    def __init__(
        self,
        store: ChannelProfileStore | None = None,
        ledger: EventLedger | None = None,
        config: ChannelIntelligenceConfig | None = None,
    ):
        self.store = store or ChannelProfileStore()
        self.ledger = ledger or EventLedger()
        self.config = config or ChannelIntelligenceConfig()
        self.scorer = ChannelScorer(self.config)

    def get_or_create_profile(self, source_name: str) -> ChannelProfile:
        profile = self.store.get(source_name)
        if profile:
            return profile

        now = datetime.now(timezone.utc).isoformat()
        profile = ChannelProfile(
            source_name=source_name,
            first_seen=now,
            last_seen=now,
            version=self.config.version,
        )
        self.store.save(profile)
        self._emit(ChannelEventType.CHANNEL_CREATED, profile, reason="Channel profile created")
        return profile

    def record_parsed_signal(self, parsed_signal: ParsedSignal) -> ChannelProfile:
        profile = self.get_or_create_profile(parsed_signal.source)
        stats = profile.rolling_statistics
        updated_stats = replace(
            stats,
            signals_received=stats.signals_received + 1,
            parsed_signals=stats.parsed_signals + 1,
            valid_signals=stats.valid_signals
            + (1 if parsed_signal.status == ParsedSignalStatus.VALID_SIGNAL else 0),
        )

        return self._update_profile(profile, updated_stats, "Parsed signal recorded")

    def record_trade_result(
        self,
        source_name: str,
        result: dict,
        execution_mode: str = "paper",
    ) -> ChannelProfile:
        profile = self.get_or_create_profile(source_name)
        stats = profile.rolling_statistics
        realized_r = float(result.get("realized_r") or 0.0)
        closed_delta = 1

        wins = stats.wins + (1 if realized_r > 0 else 0)
        losses = stats.losses + (1 if realized_r < 0 else 0)
        breakeven = stats.breakeven + (1 if realized_r == 0 else 0)
        closed_trades = stats.closed_trades + closed_delta
        total_rr = stats.total_rr + realized_r
        gross_win = stats.gross_win + (realized_r if realized_r > 0 else 0.0)
        gross_loss = stats.gross_loss + abs(realized_r if realized_r < 0 else 0.0)
        cumulative_rr = stats.cumulative_rr + realized_r
        equity_peak = max(stats.equity_peak, cumulative_rr)
        current_drawdown = max(0.0, equity_peak - cumulative_rr)
        max_drawdown = max(stats.max_drawdown, current_drawdown)

        consecutive_wins = stats.consecutive_wins + 1 if realized_r > 0 else 0
        consecutive_losses = stats.consecutive_losses + 1 if realized_r < 0 else 0
        win_rate = wins / closed_trades if closed_trades else 0.0
        expectancy = total_rr / closed_trades if closed_trades else 0.0
        profit_factor = gross_win / gross_loss if gross_loss else None
        average_rr = expectancy
        stability_score = self._stability_score(max_drawdown)
        consistency_score = self._consistency_score(
            consecutive_losses=consecutive_losses,
            closed_trades=closed_trades,
        )

        period_key = self._period_key(result)
        daily_returns = self._increment_return(stats.daily_returns, period_key["day"], realized_r)
        weekly_returns = self._increment_return(stats.weekly_returns, period_key["week"], realized_r)
        monthly_returns = self._increment_return(
            stats.monthly_returns,
            period_key["month"],
            realized_r,
        )

        updated_stats = replace(
            stats,
            executed_paper=stats.executed_paper + (1 if execution_mode == "paper" else 0),
            executed_live=stats.executed_live + (1 if execution_mode == "live" else 0),
            wins=wins,
            losses=losses,
            breakeven=breakeven,
            average_rr=average_rr,
            expectancy=expectancy,
            profit_factor=profit_factor,
            win_rate=win_rate,
            average_hold_time=self._running_average(
                stats.average_hold_time,
                closed_trades,
                self._hold_time_seconds(result),
            ),
            average_stop_distance=self._running_average(
                stats.average_stop_distance,
                closed_trades,
                float(result.get("stop_distance") or 0.0),
            ),
            average_tp_distance=self._running_average(
                stats.average_tp_distance,
                closed_trades,
                float(result.get("tp_distance") or 0.0),
            ),
            largest_win=max(stats.largest_win, realized_r),
            largest_loss=min(stats.largest_loss, realized_r),
            current_drawdown=current_drawdown,
            max_drawdown=max_drawdown,
            consecutive_losses=consecutive_losses,
            consecutive_wins=consecutive_wins,
            stability_score=stability_score,
            consistency_score=consistency_score,
            monthly_returns=monthly_returns,
            weekly_returns=weekly_returns,
            daily_returns=daily_returns,
            gross_win=gross_win,
            gross_loss=gross_loss,
            total_rr=total_rr,
            closed_trades=closed_trades,
            equity_peak=equity_peak,
            cumulative_rr=cumulative_rr,
        )

        return self._update_profile(profile, updated_stats, "Trade result recorded")

    def record_backtest_result(self, source_name: str, result: dict) -> ChannelProfile:
        if result.get("status") not in {"WIN", "LOSS", "CLOSED"}:
            return self.get_or_create_profile(source_name)

        return self.record_trade_result(
            source_name=source_name,
            result=result,
            execution_mode="paper",
        )

    def set_manual_override(
        self,
        source_name: str,
        override: ManualOverride,
        reason: str | None = None,
    ) -> ChannelProfile:
        profile = self.get_or_create_profile(source_name)
        decision = self._manual_decision(override, reason)
        updated = replace(
            profile,
            manual_override=override,
            approval_state=ApprovalState.MANUAL_OVERRIDE
            if override != ManualOverride.NONE
            else ApprovalState.AUTOMATIC,
            grade=decision.grade,
            paper_enabled=decision.grade in {ChannelGrade.PAPER, ChannelGrade.PROMOTING, ChannelGrade.LIVE},
            live_enabled=decision.grade == ChannelGrade.LIVE,
            approval_reason=decision.reason,
            last_seen=datetime.now(timezone.utc).isoformat(),
        )
        self.store.save(updated)
        self._emit(ChannelEventType.CHANNEL_UPDATED, updated, reason=decision.reason)
        return updated

    def evaluate_source(self, source_name: str) -> DecisionContext:
        profile = self.get_or_create_profile(source_name)
        decision = self._promotion_decision(profile)
        return DecisionContext(
            source_name=profile.source_name,
            channel_score=profile.score,
            grade=profile.grade,
            approval_state=profile.approval_state,
            manual_override=profile.manual_override,
            paper_enabled=profile.paper_enabled,
            live_enabled=profile.live_enabled,
            promotion_decision=decision,
            approval_reason=profile.approval_reason or decision.reason,
        )

    def _update_profile(
        self,
        profile: ChannelProfile,
        stats: RollingStatistics,
        reason: str,
    ) -> ChannelProfile:
        score = self.scorer.score(stats)
        scored = replace(
            profile,
            rolling_statistics=stats,
            score=score,
            last_seen=datetime.now(timezone.utc).isoformat(),
        )
        decision = self._promotion_decision(scored)
        updated = replace(
            scored,
            grade=decision.grade,
            paper_enabled=decision.grade in {ChannelGrade.PAPER, ChannelGrade.PROMOTING, ChannelGrade.LIVE},
            live_enabled=decision.grade == ChannelGrade.LIVE,
            approval_reason=decision.reason,
            approval_state=ApprovalState.MANUAL_OVERRIDE
            if scored.manual_override != ManualOverride.NONE
            else ApprovalState.AUTOMATIC,
        )
        self.store.save(updated)
        self._emit(ChannelEventType.CHANNEL_METRICS_UPDATED, updated, reason=reason)
        self._emit(ChannelEventType.CHANNEL_SCORE_UPDATED, updated, reason=decision.reason)
        self._emit_transition(decision, updated)
        return updated

    def _promotion_decision(self, profile: ChannelProfile) -> PromotionDecision:
        if profile.manual_override != ManualOverride.NONE:
            return self._manual_decision(profile.manual_override, profile.approval_reason)

        stats = profile.rolling_statistics
        thresholds = self.config.thresholds

        if stats.consecutive_losses >= thresholds.reject_loss_streak:
            return PromotionDecision(
                action=PromotionAction.REJECT,
                grade=ChannelGrade.REJECTED,
                reason="Loss streak exceeded rejection threshold",
            )

        if (
            stats.consecutive_losses >= thresholds.pause_loss_streak
            or stats.max_drawdown > thresholds.maximum_drawdown
        ):
            return PromotionDecision(
                action=PromotionAction.PAUSE,
                grade=ChannelGrade.PAUSED,
                reason="Risk deterioration threshold reached",
            )

        if stats.closed_trades < thresholds.minimum_signals:
            return PromotionDecision(
                action=PromotionAction.HOLD,
                grade=ChannelGrade.OBSERVE,
                reason="Insufficient sample size",
            )

        passes_quality = (
            stats.win_rate >= thresholds.minimum_win_rate
            and stats.expectancy >= thresholds.minimum_expectancy
            and stats.average_rr >= thresholds.minimum_rr
            and stats.consecutive_losses <= thresholds.maximum_loss_streak
            and stats.stability_score >= thresholds.minimum_stability
            and (stats.profit_factor or 0.0) >= thresholds.minimum_profit_factor
        )

        if not passes_quality:
            return PromotionDecision(
                action=PromotionAction.DEMOTE,
                grade=ChannelGrade.OBSERVE,
                reason="Channel quality below promotion thresholds",
            )

        if profile.score >= thresholds.live_score:
            return PromotionDecision(
                action=PromotionAction.PROMOTE,
                grade=ChannelGrade.LIVE,
                reason="Channel meets live promotion thresholds",
            )

        if profile.score >= thresholds.promoting_score:
            return PromotionDecision(
                action=PromotionAction.PROMOTE,
                grade=ChannelGrade.PROMOTING,
                reason="Channel meets promoting thresholds",
            )

        if profile.score >= thresholds.paper_score:
            return PromotionDecision(
                action=PromotionAction.PROMOTE,
                grade=ChannelGrade.PAPER,
                reason="Channel meets paper thresholds",
            )

        return PromotionDecision(
            action=PromotionAction.HOLD,
            grade=ChannelGrade.OBSERVE,
            reason="Channel score below paper threshold",
        )

    def _manual_decision(
        self,
        override: ManualOverride,
        reason: str | None,
    ) -> PromotionDecision:
        reason = reason or f"Manual override: {override.value}"
        mapping = {
            ManualOverride.FORCE_OBSERVE: (PromotionAction.HOLD, ChannelGrade.OBSERVE),
            ManualOverride.FORCE_PAPER: (PromotionAction.PROMOTE, ChannelGrade.PAPER),
            ManualOverride.FORCE_LIVE: (PromotionAction.PROMOTE, ChannelGrade.LIVE),
            ManualOverride.FORCE_REJECT: (PromotionAction.REJECT, ChannelGrade.REJECTED),
            ManualOverride.NONE: (PromotionAction.HOLD, ChannelGrade.UNKNOWN),
        }
        action, grade = mapping[override]
        return PromotionDecision(action=action, grade=grade, reason=reason)

    def _emit_transition(self, decision: PromotionDecision, profile: ChannelProfile):
        event_type = {
            PromotionAction.PROMOTE: ChannelEventType.CHANNEL_PROMOTED,
            PromotionAction.DEMOTE: ChannelEventType.CHANNEL_DEMOTED,
            PromotionAction.PAUSE: ChannelEventType.CHANNEL_PAUSED,
            PromotionAction.REJECT: ChannelEventType.CHANNEL_REJECTED,
            PromotionAction.HOLD: ChannelEventType.CHANNEL_UPDATED,
        }[decision.action]
        self._emit(event_type, profile, reason=decision.reason)

    def _emit(
        self,
        event_type: ChannelEventType,
        profile: ChannelProfile,
        reason: str | None,
    ):
        self.ledger.append(
            DecisionEvent(
                stage="channel_intelligence",
                input_id=profile.source_name,
                output_id=profile.id,
                reason=reason,
                version=profile.version,
                payload={
                    "event_type": event_type.value,
                    "profile": profile.to_dict(),
                },
            )
        )

    def _stability_score(self, max_drawdown: float) -> float:
        maximum_drawdown = self.config.thresholds.maximum_drawdown
        if maximum_drawdown <= 0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - (max_drawdown / maximum_drawdown)))

    def _consistency_score(self, consecutive_losses: int, closed_trades: int) -> float:
        if closed_trades <= 0:
            return 0.0
        maximum_loss_streak = self.config.thresholds.maximum_loss_streak
        if maximum_loss_streak <= 0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - (consecutive_losses / maximum_loss_streak)))

    def _running_average(self, previous_average: float, count: int, value: float) -> float:
        if count <= 1:
            return value
        return previous_average + ((value - previous_average) / count)

    def _hold_time_seconds(self, result: dict) -> float:
        opened_at = result.get("opened_at") or result.get("posted_at")
        closed_at = result.get("closed_at") or result.get("exit_time")
        if not opened_at or not closed_at:
            return 0.0

        start = datetime.fromisoformat(str(opened_at).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(closed_at).replace("Z", "+00:00"))
        return max(0.0, (end - start).total_seconds())

    def _period_key(self, result: dict) -> dict:
        raw_time = (
            result.get("closed_at")
            or result.get("exit_time")
            or datetime.now(timezone.utc).isoformat()
        )
        dt = datetime.fromisoformat(str(raw_time).replace("Z", "+00:00"))
        year, week, _ = dt.isocalendar()
        return {
            "day": dt.date().isoformat(),
            "week": f"{year}-W{week:02d}",
            "month": f"{dt.year}-{dt.month:02d}",
        }

    def _increment_return(self, returns: dict[str, float], key: str, value: float):
        updated = dict(returns)
        updated[key] = round(updated.get(key, 0.0) + value, 10)
        return updated
