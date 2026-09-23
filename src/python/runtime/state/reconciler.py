"""Orchestrate REST snapshot + open orders → AccountState. P1."""
from __future__ import annotations

from typing import Protocol

from src.python.exchange.models.account import AccountSnapshot, OpenOrder
from src.python.runtime.state.store import InMemoryAccountStateStore, detect_snapshot_conflict


class AccountDataSource(Protocol):
    def get_account_snapshot(self) -> AccountSnapshot: ...

    def get_open_orders(self) -> list[OpenOrder]: ...


class AccountReconciler:
    def __init__(self, store: InMemoryAccountStateStore, source: AccountDataSource) -> None:
        self._store = store
        self._source = source

    def full_resync(self, *, detect_conflict_asset: str | None = "USDT") -> None:
        try:
            prev = self._store.get()
            snapshot = self._source.get_account_snapshot()
            orders = self._source.get_open_orders()
            if (
                detect_conflict_asset
                and prev.snapshot is not None
                and prev.reconciliation_status.value
                in ("RECONCILED", "STALE", "DIVERGED")
            ):
                if detect_snapshot_conflict(
                    snapshot, prev.snapshot, asset=detect_conflict_asset
                ):
                    self._store.apply_rest_snapshot(snapshot, orders)
                    return
            self._store.apply_rest_snapshot(snapshot, orders)
        except Exception as exc:
            self._store.mark_rest_error()
            self._store.mark_unknown(f"rest_error:{type(exc).__name__}")
            raise

    def on_ws_disconnect(self) -> None:
        self._store.mark_ws_disconnect()

    def on_ws_reconnected(self) -> None:
        self.full_resync()
