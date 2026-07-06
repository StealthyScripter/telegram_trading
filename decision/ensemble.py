from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from contracts.trade_candidate import TradeCandidate, TradeCandidateStatus
from events.ledger import EventLedger
from events.models import DecisionEvent


class EnsembleEventType(str, Enum):
    ENSEMBLE_CREATED = "ENSEMBLE_CREATED"
    ENSEMBLE_CONFLICT_DETECTED = "ENSEMBLE_CONFLICT_DETECTED"
    ENSEMBLE_APPROVED = "ENSEMBLE_APPROVED"
    ENSEMBLE_REJECTED = "ENSEMBLE_REJECTED"


@dataclass(frozen=True)
class EnsembleConfig:
    consensus_threshold: float = 0.6
    conflict_threshold: float = 0.4
    max_signal_age_seconds: int = 3600
    min_sources_required: int = 1
    allow_single_source: bool = True
    source_weighting_enabled: bool = True
    minimum_confidence: float = 0.0


@dataclass(frozen=True)
class EnsembleVote:
    candidate_id: str
    source: str
    symbol: str
    action: str
    weight: float


@dataclass(frozen=True)
class ConflictResult:
    conflict_detected: bool
    reason: str | None = None


@dataclass(frozen=True)
class ConsensusScore:
    symbol: str | None
    action: str | None
    score: float
    total_weight: float
    source_count: int


@dataclass(frozen=True)
class EnsembleSignal:
    id: str = field(default_factory=lambda: str(uuid4()))
    votes: list[EnsembleVote] = field(default_factory=list)
    ignored_candidate_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EnsembleDecision:
    approved: bool
    reason: str
    consensus_score: ConsensusScore
    candidate: TradeCandidate | None = None
    ensemble: EnsembleSignal | None = None
    conflict: ConflictResult = field(default_factory=lambda: ConflictResult(False))


class EnsembleDecisionEngine:
    def __init__(
        self,
        config: EnsembleConfig | None = None,
        ledger: EventLedger | None = None,
        source_scores: dict[str, float] | None = None,
    ):
        self.config = config or EnsembleConfig()
        self.ledger = ledger or EventLedger()
        self.source_scores = source_scores or {}

    def evaluate(
        self,
        candidates: list[TradeCandidate],
        now: datetime | None = None,
    ) -> EnsembleDecision:
        now = now or datetime.now(timezone.utc)
        votes, ignored = self._votes(candidates, now)
        ensemble = EnsembleSignal(votes=votes, ignored_candidate_ids=ignored)
        self._emit(EnsembleEventType.ENSEMBLE_CREATED, ensemble, None, "Ensemble created")

        if not votes:
            return self._reject(
                ensemble=ensemble,
                reason="No eligible candidates",
                conflict=ConflictResult(False),
            )

        source_count = len({vote.source for vote in votes})
        if source_count < self.config.min_sources_required:
            return self._reject(
                ensemble=ensemble,
                reason="Insufficient source count",
                conflict=ConflictResult(False),
            )

        if source_count == 1 and not self.config.allow_single_source:
            return self._reject(
                ensemble=ensemble,
                reason="Single source ensembles are disabled",
                conflict=ConflictResult(False),
            )

        conflict = self._conflict(votes)
        if conflict.conflict_detected:
            self._emit(
                EnsembleEventType.ENSEMBLE_CONFLICT_DETECTED,
                ensemble,
                None,
                conflict.reason,
            )
            return self._reject(ensemble, conflict.reason or "Conflict detected", conflict)

        consensus = self._consensus(votes)
        if consensus.score < self.config.consensus_threshold:
            return self._reject(
                ensemble=ensemble,
                reason="Consensus score below threshold",
                conflict=ConflictResult(False),
                consensus=consensus,
            )

        representative = self._representative(candidates, consensus)
        if representative is None:
            return self._reject(
                ensemble=ensemble,
                reason="No representative candidate found",
                conflict=ConflictResult(False),
                consensus=consensus,
            )

        candidate = replace(
            representative,
            status=TradeCandidateStatus.APPROVED_FOR_RISK,
            reason="Ensemble consensus approved",
        )
        decision = EnsembleDecision(
            approved=True,
            reason="Ensemble consensus approved",
            consensus_score=consensus,
            candidate=candidate,
            ensemble=ensemble,
        )
        self._emit(EnsembleEventType.ENSEMBLE_APPROVED, ensemble, decision, decision.reason)
        return decision

    def _votes(self, candidates: list[TradeCandidate], now: datetime):
        votes = []
        ignored = []
        seen_sources = set()

        for candidate in candidates:
            if candidate.id in ignored:
                continue

            if not self._eligible(candidate):
                ignored.append(candidate.id)
                continue

            if self._is_stale(candidate, now):
                ignored.append(candidate.id)
                continue

            if candidate.source in seen_sources:
                ignored.append(candidate.id)
                continue

            seen_sources.add(candidate.source)
            votes.append(
                EnsembleVote(
                    candidate_id=candidate.id,
                    source=candidate.source,
                    symbol=candidate.symbol or "",
                    action=candidate.action or "",
                    weight=self._source_weight(candidate.source),
                )
            )

        return votes, ignored

    def _eligible(self, candidate: TradeCandidate) -> bool:
        if candidate.status not in {
            TradeCandidateStatus.APPROVED_FOR_RISK,
            TradeCandidateStatus.PAPER_ONLY,
        }:
            return False

        if not candidate.symbol or candidate.action not in {"buy", "sell"}:
            return False

        if candidate.confidence is not None and candidate.confidence < self.config.minimum_confidence:
            return False

        return True

    def _is_stale(self, candidate: TradeCandidate, now: datetime) -> bool:
        created_at = datetime.fromisoformat(candidate.created_at.replace("Z", "+00:00"))
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return (now - created_at).total_seconds() > self.config.max_signal_age_seconds

    def _source_weight(self, source: str) -> float:
        if not self.config.source_weighting_enabled:
            return 1.0
        score = self.source_scores.get(source, 100)
        return max(0.0, min(1.0, score / 100))

    def _conflict(self, votes: list[EnsembleVote]) -> ConflictResult:
        by_symbol = {}
        for vote in votes:
            by_symbol.setdefault(vote.symbol, {}).setdefault(vote.action, 0.0)
            by_symbol[vote.symbol][vote.action] += vote.weight

        for symbol, actions in by_symbol.items():
            total = sum(actions.values())
            if total <= 0:
                continue
            buy_ratio = actions.get("buy", 0.0) / total
            sell_ratio = actions.get("sell", 0.0) / total
            if buy_ratio >= self.config.conflict_threshold and sell_ratio >= self.config.conflict_threshold:
                return ConflictResult(
                    conflict_detected=True,
                    reason=f"Conflicting buy/sell signals for {symbol}",
                )

        return ConflictResult(False)

    def _consensus(self, votes: list[EnsembleVote]) -> ConsensusScore:
        grouped = {}
        for vote in votes:
            key = (vote.symbol, vote.action)
            grouped[key] = grouped.get(key, 0.0) + vote.weight

        total_weight = sum(vote.weight for vote in votes)
        if total_weight <= 0:
            return ConsensusScore(None, None, 0.0, 0.0, 0)

        (symbol, action), weight = max(grouped.items(), key=lambda item: item[1])
        return ConsensusScore(
            symbol=symbol,
            action=action,
            score=weight / total_weight,
            total_weight=total_weight,
            source_count=len({vote.source for vote in votes}),
        )

    def _representative(
        self,
        candidates: list[TradeCandidate],
        consensus: ConsensusScore,
    ) -> TradeCandidate | None:
        matching = [
            candidate for candidate in candidates
            if candidate.symbol == consensus.symbol
            and candidate.action == consensus.action
            and self._eligible(candidate)
        ]
        if not matching:
            return None
        return matching[0]

    def _reject(
        self,
        ensemble: EnsembleSignal,
        reason: str,
        conflict: ConflictResult,
        consensus: ConsensusScore | None = None,
    ) -> EnsembleDecision:
        decision = EnsembleDecision(
            approved=False,
            reason=reason,
            consensus_score=consensus or ConsensusScore(None, None, 0.0, 0.0, 0),
            ensemble=ensemble,
            conflict=conflict,
        )
        self._emit(EnsembleEventType.ENSEMBLE_REJECTED, ensemble, decision, reason)
        return decision

    def _emit(
        self,
        event_type: EnsembleEventType,
        ensemble: EnsembleSignal,
        decision: EnsembleDecision | None,
        reason: str | None,
    ):
        self.ledger.append(
            DecisionEvent(
                stage="ensemble",
                input_id=",".join(vote.candidate_id for vote in ensemble.votes) or None,
                output_id=ensemble.id,
                reason=reason,
                payload={
                    "event_type": event_type.value,
                    "ensemble_id": ensemble.id,
                    "votes": [vote.__dict__ for vote in ensemble.votes],
                    "ignored_candidate_ids": ensemble.ignored_candidate_ids,
                    "approved": decision.approved if decision else None,
                    "consensus_score": decision.consensus_score.__dict__ if decision else None,
                },
            )
        )
