"""P0 Contract: AccountState — SSOT for balances, positions, open orders.

LOCKED:
  - Built only from REST snapshot + private stream events + reconciliation
  - GUI / Telegram / sizing / reporting MUST read from AccountState
  - Never invent balances or positions
  - Reconciliation UNKNOWN → BLOCK execution
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from src.python.exchange.models.account import AccountSnapshot, OpenOrder


class ReconciliationStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    IN_PROGRESS = "IN_PROGRESS"
    RECONCILED = "RECONCILED"
    DIVERGED = "DIVERGED"
    STALE = "STALE"


@dataclass
class AccountState:
    """Single Source of Truth. Do not mutate outside reconciliation path."""

    snapshot: Optional[AccountSnapshot] = None
    open_orders: list[OpenOrder] = field(default_factory=list)
    reconciliation_status: ReconciliationStatus = ReconciliationStatus.UNKNOWN
    last_reconciled_at_ms: Optional[int] = None
    last_private_event_at_ms: Optional[int] = None
    source: str = "uninitialized"

    def is_ready_for_execution(self) -> bool:
        """Fail-closed: only RECONCILED state allows sizing / execution."""
        return (
            self.reconciliation_status == ReconciliationStatus.RECONCILED
            and self.snapshot is not None
        )


class AccountStateStore(ABC):
    """Manages the SSOT. All readers go through this."""

    @abstractmethod
    def get(self) -> AccountState: ...

    @abstractmethod
    def apply_rest_snapshot(self, snapshot: AccountSnapshot, open_orders: list[OpenOrder]) -> None: ...

    @abstractmethod
    def apply_private_event(self, event: dict[str, Any]) -> None: ...

    @abstractmethod
    def mark_stale(self, reason: str) -> None: ...
