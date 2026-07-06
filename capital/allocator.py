from dataclasses import asdict
from decimal import Decimal
from enum import Enum

from contracts.capital_allocation import CapitalAllocation
from contracts.risk_decision import RiskDecision, RiskDecisionStatus
from contracts.trade_candidate import TradeCandidate
from decision.channel_intelligence import DecisionContext
from events.ledger import EventLedger
from events.models import DecisionEvent

from capital.models import (
    AccountCapitalState,
    AccountMode,
    AllocationConfig,
    AllocationDecision,
)


class CapitalEventType(str, Enum):
    CAPITAL_ALLOCATION_CREATED = "CAPITAL_ALLOCATION_CREATED"
    CAPITAL_ALLOCATION_REJECTED = "CAPITAL_ALLOCATION_REJECTED"
    CAPITAL_ALLOCATION_CLAMPED = "CAPITAL_ALLOCATION_CLAMPED"
    CAPITAL_ALLOCATION_UPDATED = "CAPITAL_ALLOCATION_UPDATED"


class CapitalAllocator:
    def __init__(
        self,
        config: AllocationConfig | None = None,
        ledger: EventLedger | None = None,
    ):
        self.config = config or AllocationConfig()
        self.ledger = ledger or EventLedger()

    def allocate(
        self,
        candidate: TradeCandidate,
        risk_decision: RiskDecision,
        account_state: AccountCapitalState | None = None,
        decision_context: DecisionContext | None = None,
        expected_entry_price: str | float | None = None,
        current_price: str | float | None = None,
        volatility: str | float | None = None,
        confidence: str | float | None = None,
        portfolio_risk_multiplier: str | float | None = None,
        units: int | None = None,
        broker: str = "oanda",
        account_id: str | None = None,
        strategy_account: str | None = None,
    ) -> CapitalAllocation:
        if units is not None:
            return self._legacy_allocate(
                candidate=candidate,
                risk_decision=risk_decision,
                units=units,
                broker=broker,
                account_id=account_id,
                strategy_account=strategy_account,
            )

        if account_state is None:
            raise ValueError("AccountCapitalState is required when units are not provided")

        allocation_decision = self.decide(
            candidate=candidate,
            risk_decision=risk_decision,
            account_state=account_state,
            decision_context=decision_context,
            expected_entry_price=expected_entry_price,
            current_price=current_price,
            volatility=volatility,
            confidence=confidence,
            portfolio_risk_multiplier=portfolio_risk_multiplier,
        )

        if not allocation_decision.approved:
            self._emit(
                event_type=CapitalEventType.CAPITAL_ALLOCATION_REJECTED,
                candidate=candidate,
                risk_decision=risk_decision,
                account_state=account_state,
                decision=allocation_decision,
                allocation=None,
            )
            raise ValueError(allocation_decision.reason)

        allocation = CapitalAllocation(
            risk_decision_id=risk_decision.id,
            symbol=candidate.symbol or "",
            action=candidate.action or "",
            units=allocation_decision.clamped_units,
            broker=account_state.broker,
            account_id=account_state.account_id,
            strategy_account=candidate.strategy_account,
            risk_amount=allocation_decision.risk_amount,
            risk_percent=allocation_decision.risk_percent,
            calculated_units=allocation_decision.calculated_units,
            reason=allocation_decision.reason,
        )

        if allocation_decision.clamped_units != allocation_decision.calculated_units:
            self._emit(
                event_type=CapitalEventType.CAPITAL_ALLOCATION_CLAMPED,
                candidate=candidate,
                risk_decision=risk_decision,
                account_state=account_state,
                decision=allocation_decision,
                allocation=allocation,
            )

        self._emit(
            event_type=CapitalEventType.CAPITAL_ALLOCATION_CREATED,
            candidate=candidate,
            risk_decision=risk_decision,
            account_state=account_state,
            decision=allocation_decision,
            allocation=allocation,
        )

        return allocation

    def decide(
        self,
        candidate: TradeCandidate,
        risk_decision: RiskDecision,
        account_state: AccountCapitalState,
        decision_context: DecisionContext | None = None,
        expected_entry_price: str | float | None = None,
        current_price: str | float | None = None,
        volatility: str | float | None = None,
        confidence: str | float | None = None,
        portfolio_risk_multiplier: str | float | None = None,
    ) -> AllocationDecision:
        if risk_decision.status != RiskDecisionStatus.APPROVED:
            return AllocationDecision(
                approved=False,
                reason=risk_decision.reason or "Risk decision is not approved",
            )

        if risk_decision.trade_candidate_id != candidate.id:
            return AllocationDecision(
                approved=False,
                reason="Risk decision does not match trade candidate",
            )

        invalid_state_reason = self._invalid_account_state_reason(account_state)
        if invalid_state_reason:
            return AllocationDecision(
                approved=False,
                reason=invalid_state_reason,
            )

        if not candidate.stop_loss:
            return AllocationDecision(
                approved=False,
                reason="Missing stop loss",
            )

        entry_price = self._select_entry_price(
            candidate=candidate,
            expected_entry_price=expected_entry_price,
            current_price=current_price,
        )

        if entry_price is None:
            return AllocationDecision(
                approved=False,
                reason="Missing entry price",
            )

        stop_loss = self._to_float(candidate.stop_loss, "stop loss")

        if entry_price <= 0 or stop_loss <= 0:
            return AllocationDecision(
                approved=False,
                reason="Entry price and stop loss must be positive",
            )

        entry_decimal = Decimal(str(entry_price))
        stop_decimal = Decimal(str(stop_loss))
        stop_distance_decimal = abs(entry_decimal - stop_decimal)
        stop_distance = float(stop_distance_decimal)

        if stop_distance_decimal <= 0:
            return AllocationDecision(
                approved=False,
                reason="Stop distance must be greater than zero",
            )

        risk_percent = self._risk_percent(
            risk_decision=risk_decision,
            account_state=account_state,
            decision_context=decision_context,
            candidate=candidate,
            volatility=volatility,
            confidence=confidence,
            portfolio_risk_multiplier=portfolio_risk_multiplier,
        )

        if risk_percent <= 0:
            return AllocationDecision(
                approved=False,
                reason="Risk percent must be greater than zero",
            )

        risk_amount_decimal = Decimal(str(account_state.equity)) * Decimal(str(risk_percent))
        risk_amount = float(risk_amount_decimal)

        if risk_decision.max_risk_amount is not None:
            risk_amount = min(risk_amount, risk_decision.max_risk_amount)
            risk_amount_decimal = Decimal(str(risk_amount))

        calculated_units = int(risk_amount_decimal / stop_distance_decimal)

        if self.config.maximum_position_value is not None:
            max_position_units = int(self.config.maximum_position_value / entry_price)
            calculated_units = min(calculated_units, max_position_units)

        if calculated_units <= 0:
            return AllocationDecision(
                approved=False,
                reason="Calculated units must be greater than zero",
                risk_amount=risk_amount,
                risk_percent=risk_percent,
            )

        clamped_units = max(
            self.config.min_units,
            min(calculated_units, self.config.max_units),
        )

        explanation = self._allocation_explanation(
            candidate=candidate,
            risk_decision=risk_decision,
            account_state=account_state,
            decision_context=decision_context,
            entry_price=entry_price,
            stop_loss=stop_loss,
            stop_distance=stop_distance,
            volatility=volatility,
            confidence=confidence,
            portfolio_risk_multiplier=portfolio_risk_multiplier,
            calculated_units=calculated_units,
            clamped_units=clamped_units,
        )

        return AllocationDecision(
            approved=True,
            reason=self._approved_reason(explanation),
            risk_amount=risk_amount,
            risk_percent=risk_percent,
            calculated_units=calculated_units,
            clamped_units=clamped_units,
            explanation=explanation,
        )

    def _legacy_allocate(
        self,
        candidate: TradeCandidate,
        risk_decision: RiskDecision,
        units: int,
        broker: str,
        account_id: str | None,
        strategy_account: str | None,
    ) -> CapitalAllocation:
        if risk_decision.status != RiskDecisionStatus.APPROVED:
            raise ValueError("Cannot allocate capital for rejected risk decision")

        return CapitalAllocation(
            risk_decision_id=risk_decision.id,
            symbol=candidate.symbol or "",
            action=candidate.action or "",
            units=units,
            broker=broker,
            account_id=account_id,
            strategy_account=strategy_account,
            reason="Capital scaffold allocation",
        )

    def _risk_percent(
        self,
        risk_decision: RiskDecision,
        account_state: AccountCapitalState,
        decision_context: DecisionContext | None,
        candidate: TradeCandidate | None = None,
        volatility: str | float | None = None,
        confidence: str | float | None = None,
        portfolio_risk_multiplier: str | float | None = None,
    ) -> float:
        risk_percent = max(
            self.config.min_risk_percent,
            min(self.config.base_risk_percent, self.config.max_risk_percent),
        )

        if risk_decision.max_risk_percent is not None:
            risk_percent = min(risk_percent, risk_decision.max_risk_percent)

        multiplier = (
            self.config.paper_multiplier
            if account_state.mode == AccountMode.PAPER
            else self.config.live_multiplier
        )
        risk_percent *= multiplier

        if self.config.enable_channel_weighting and decision_context is not None:
            if decision_context.channel_score < self.config.minimum_channel_score:
                return 0.0

            risk_percent *= self._channel_multiplier(decision_context.channel_score)

        if self.config.enable_confidence_weighting and confidence is not None:
            risk_percent *= self._confidence_multiplier(confidence)

        if self.config.enable_strategy_weighting and candidate is not None:
            risk_percent *= self._strategy_multiplier(candidate.strategy_account)

        if self.config.enable_volatility_adjustment and volatility is not None:
            risk_percent *= self._volatility_multiplier(volatility)

        if self.config.enable_portfolio_risk_adjustment:
            risk_percent *= self._portfolio_multiplier(portfolio_risk_multiplier)

        return risk_percent

    def _channel_multiplier(self, channel_score: float) -> float:
        for rule in sorted(
            self.config.channel_weight_rules,
            key=lambda item: item.minimum_score,
            reverse=True,
        ):
            if channel_score >= rule.minimum_score:
                return rule.multiplier

        return 0.0

    def _confidence_multiplier(self, confidence: str | float) -> float:
        value = self._bounded_float(confidence, "confidence", minimum=0.0, maximum=1.0)
        return max(self.config.minimum_confidence_multiplier, value)

    def _strategy_multiplier(self, strategy_account: str | None) -> float:
        if not strategy_account:
            return self.config.default_strategy_multiplier

        return self.config.strategy_weight_rules.get(
            strategy_account,
            self.config.default_strategy_multiplier,
        )

    def _volatility_multiplier(self, volatility: str | float) -> float:
        value = self._bounded_float(volatility, "volatility", minimum=0.0)
        if value == 0:
            return self.config.maximum_volatility_multiplier

        raw_multiplier = self.config.target_volatility / value
        return max(
            self.config.minimum_volatility_multiplier,
            min(raw_multiplier, self.config.maximum_volatility_multiplier),
        )

    def _portfolio_multiplier(self, portfolio_risk_multiplier: str | float | None) -> float:
        if portfolio_risk_multiplier is None:
            return self.config.portfolio_risk_multiplier

        return self._bounded_float(
            portfolio_risk_multiplier,
            "portfolio risk multiplier",
            minimum=0.0,
        )

    def _invalid_account_state_reason(self, account_state: AccountCapitalState) -> str | None:
        if account_state.equity <= 0:
            return "Invalid capital state: equity must be greater than zero"

        if account_state.available_margin <= 0:
            return "Invalid capital state: available margin must be greater than zero"

        if account_state.balance < 0:
            return "Invalid capital state: balance cannot be negative"

        return None

    def _select_entry_price(
        self,
        candidate: TradeCandidate,
        expected_entry_price: str | float | None,
        current_price: str | float | None,
    ) -> float | None:
        raw_price = candidate.entry_price or expected_entry_price or current_price

        if raw_price is None:
            return None

        return self._to_float(raw_price, "entry price")

    def _to_float(self, value, label: str) -> float:
        try:
            return float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid {label}") from error

    def _bounded_float(
        self,
        value,
        label: str,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> float:
        parsed = self._to_float(value, label)
        if minimum is not None and parsed < minimum:
            raise ValueError(f"Invalid {label}")
        if maximum is not None and parsed > maximum:
            raise ValueError(f"Invalid {label}")
        return parsed

    def _allocation_explanation(
        self,
        candidate: TradeCandidate,
        risk_decision: RiskDecision,
        account_state: AccountCapitalState,
        decision_context: DecisionContext | None,
        entry_price: float,
        stop_loss: float,
        stop_distance: float,
        volatility: str | float | None,
        confidence: str | float | None,
        portfolio_risk_multiplier: str | float | None,
        calculated_units: int,
        clamped_units: int,
    ) -> dict:
        mode_multiplier = (
            self.config.paper_multiplier
            if account_state.mode == AccountMode.PAPER
            else self.config.live_multiplier
        )
        channel_multiplier = 1.0
        if self.config.enable_channel_weighting and decision_context is not None:
            channel_multiplier = self._channel_multiplier(decision_context.channel_score)

        confidence_multiplier = (
            self._confidence_multiplier(confidence)
            if self.config.enable_confidence_weighting and confidence is not None
            else 1.0
        )
        strategy_multiplier = (
            self._strategy_multiplier(candidate.strategy_account)
            if self.config.enable_strategy_weighting
            else 1.0
        )
        volatility_multiplier = (
            self._volatility_multiplier(volatility)
            if self.config.enable_volatility_adjustment and volatility is not None
            else 1.0
        )
        portfolio_multiplier = (
            self._portfolio_multiplier(portfolio_risk_multiplier)
            if self.config.enable_portfolio_risk_adjustment
            else 1.0
        )

        return {
            "base_risk_percent": self.config.base_risk_percent,
            "risk_decision_max_risk_percent": risk_decision.max_risk_percent,
            "risk_decision_max_risk_amount": risk_decision.max_risk_amount,
            "mode": account_state.mode.value,
            "mode_multiplier": mode_multiplier,
            "channel_score": decision_context.channel_score if decision_context else None,
            "channel_multiplier": channel_multiplier,
            "confidence": self._to_float(confidence, "confidence") if confidence is not None else None,
            "confidence_multiplier": confidence_multiplier,
            "strategy_account": candidate.strategy_account,
            "strategy_multiplier": strategy_multiplier,
            "volatility": self._to_float(volatility, "volatility") if volatility is not None else None,
            "volatility_multiplier": volatility_multiplier,
            "portfolio_risk_multiplier": portfolio_multiplier,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "stop_distance": stop_distance,
            "calculated_units": calculated_units,
            "clamped_units": clamped_units,
            "was_clamped": calculated_units != clamped_units,
        }

    def _approved_reason(self, explanation: dict) -> str:
        parts = ["Capital allocation approved"]
        if explanation["was_clamped"]:
            parts.append("units clamped")
        if explanation["volatility_multiplier"] != 1.0:
            parts.append("volatility adjusted")
        if explanation["confidence_multiplier"] != 1.0:
            parts.append("confidence weighted")
        if explanation["strategy_multiplier"] != 1.0:
            parts.append("strategy weighted")
        if explanation["portfolio_risk_multiplier"] != 1.0:
            parts.append("portfolio risk adjusted")
        return "; ".join(parts)

    def _emit(
        self,
        event_type: CapitalEventType,
        candidate: TradeCandidate,
        risk_decision: RiskDecision,
        account_state: AccountCapitalState,
        decision: AllocationDecision,
        allocation: CapitalAllocation | None,
    ):
        self.ledger.append(
            DecisionEvent(
                stage="capital_allocation",
                input_id=candidate.id,
                output_id=allocation.id if allocation else None,
                reason=decision.reason,
                payload={
                    "event_type": event_type.value,
                    "trade_candidate_id": candidate.id,
                    "risk_decision_id": risk_decision.id,
                    "account_id": account_state.account_id,
                    "broker": account_state.broker,
                    "symbol": candidate.symbol,
                    "action": candidate.action,
                    "units": allocation.units if allocation else decision.clamped_units,
                    "risk_amount": decision.risk_amount,
                    "risk_percent": decision.risk_percent,
                    "calculated_units": decision.calculated_units,
                    "clamped_units": decision.clamped_units,
                    "reason": decision.reason,
                    "explanation": decision.explanation,
                    "allocation": allocation.to_dict() if allocation else None,
                    "decision": asdict(decision),
                },
            )
        )
