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

        return AllocationDecision(
            approved=True,
            reason="Capital allocation approved",
            risk_amount=risk_amount,
            risk_percent=risk_percent,
            calculated_units=calculated_units,
            clamped_units=clamped_units,
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
                    "allocation": allocation.to_dict() if allocation else None,
                    "decision": asdict(decision),
                },
            )
        )
