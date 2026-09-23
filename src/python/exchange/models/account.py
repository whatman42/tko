"""Account and order models for P0 AccountState SSOT."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class Balance:
    asset: str
    free: str
    locked: str


@dataclass(frozen=True)
class AccountSnapshot:
    balances: tuple[Balance, ...]
    can_trade: bool = True
    update_time_ms: Optional[int] = None
    raw: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class OpenOrder:
    symbol: str
    order_id: str
    client_order_id: Optional[str]
    side: str
    order_type: str
    price: str
    orig_qty: str
    executed_qty: str
    status: str
    symbol_type: Optional[int] = None
    raw: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)
