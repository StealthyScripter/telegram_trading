from dataclasses import dataclass
from enum import Enum

from contracts.base import BaseContract


class ContractExecutionStatus(str, Enum):
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"
    FAILED = "FAILED"
    DISCREPANCY = "DISCREPANCY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ContractExecutionResult(BaseContract):
    execution_request_id: str = ""
    status: ContractExecutionStatus = ContractExecutionStatus.UNKNOWN
    broker: str = ""
    account_id: str = ""
    symbol: str = ""
    action: str = ""
    requested_units: int = 0
    broker_trade_id: str | None = None
    broker_order_id: str | None = None
    fill_price: str | None = None
    reason: str | None = None
    raw_response: dict | None = None

    def __post_init__(self):
        if not self.execution_request_id:
            raise ValueError("ContractExecutionResult.execution_request_id is required")
