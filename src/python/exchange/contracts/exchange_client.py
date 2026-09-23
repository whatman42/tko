"""P0 Contract: ExchangeClient — no order placement authority.

LOCKED: get_server_time, get_symbols, get_account_snapshot, get_open_orders only.
create_order / cancel_order are FORBIDDEN in P0 (appear only in P3 LiveOrderExecutor).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from src.python.exchange.models.instrument import InstrumentMeta
from src.python.exchange.models.account import AccountSnapshot, OpenOrder


@runtime_checkable
class ExchangeClient(Protocol):
    """Minimal read-only exchange surface for P0 foundation."""

    def get_server_time(self) -> int:
        """Return exchange server time in milliseconds."""
        ...

    def get_symbols(self) -> list[InstrumentMeta]:
        """Return full discovered instrument list (all symbolTypes)."""
        ...

    def get_account_snapshot(self) -> AccountSnapshot:
        """Return balances + locked amounts. Requires valid credentials."""
        ...

    def get_open_orders(self) -> list[OpenOrder]:
        """Return currently open orders. Requires valid credentials."""
        ...


class AbstractExchangeClient(ABC):
    """ABC form for concrete implementations (TokocryptoRestClient, etc.)."""

    @abstractmethod
    def get_server_time(self) -> int: ...

    @abstractmethod
    def get_symbols(self) -> list[InstrumentMeta]: ...

    @abstractmethod
    def get_account_snapshot(self) -> AccountSnapshot: ...

    @abstractmethod
    def get_open_orders(self) -> list[OpenOrder]: ...

    # Explicitly no create_order / cancel_order methods.
    # Any subclass that adds them in P0 is a contract violation.
