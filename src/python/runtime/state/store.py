"""Concrete AccountStateStore + reducer — P1 SSOT. No order submission."""
from __future__ import annotations

import copy
import threading
import time
from typing import Any, Optional

from src.python.exchange.contracts.account_state import (
    AccountState,
    AccountStateStore,
    ReconciliationStatus,
)
from src.python.exchange.models.account import AccountSnapshot, Balance, OpenOrder
from src.python.runtime.state.events import (
    NormalizedEvent,
    NormalizedEventType,
    normalize_private_event,
)
from src.python.runtime.state.lifecycle import AccountLifecycle, REQUIRES_REST_RESYNC

_TERMINAL_STATUSES = frozenset(
    {
        "FILLED",
        "CANCELED",
        "CANCELLED",
        "REJECTED",
        "EXPIRED",
        "EXPIRED_IN_MATCH",
    }
)


class InMemoryAccountStateStore(AccountStateStore):
    """
    Single-writer SSOT.

    Invariants:
      - UNKNOWN / STALE never exposed as zero balances for risk
      - snapshot is None until first successful REST apply
      - duplicate events ignored via event_id set
      - REST snapshot is authoritative overwrite of balances + open orders
    """

    def __init__(self, *, max_event_ids: int = 10_000) -> None:
        self._lock = threading.RLock()
        self._lifecycle = AccountLifecycle.UNINITIALIZED
        self._state = AccountState()
        self._seen_event_ids: dict[str, None] = {}
        self._max_event_ids = max_event_ids
        self._last_reason: str = ""
        self._version: int = 0

    def get(self) -> AccountState:
        with self._lock:
            return AccountState(
                snapshot=self._state.snapshot,
                open_orders=list(self._state.open_orders),
                reconciliation_status=self._state.reconciliation_status,
                last_reconciled_at_ms=self._state.last_reconciled_at_ms,
                last_private_event_at_ms=self._state.last_private_event_at_ms,
                source=self._state.source,
            )

    def lifecycle(self) -> AccountLifecycle:
        with self._lock:
            return self._lifecycle

    def last_reason(self) -> str:
        with self._lock:
            return self._last_reason

    def version(self) -> int:
        with self._lock:
            return self._version

    def balances_for_risk(self) -> Optional[tuple[Balance, ...]]:
        with self._lock:
            if self._lifecycle in (
                AccountLifecycle.UNKNOWN,
                AccountLifecycle.UNINITIALIZED,
                AccountLifecycle.SNAPSHOT_LOADING,
                AccountLifecycle.STALE,
            ):
                return None
            if self._state.reconciliation_status not in (
                ReconciliationStatus.RECONCILED,
            ):
                return None
            if self._state.snapshot is None:
                return None
            return self._state.snapshot.balances

    def apply_rest_snapshot(
        self,
        snapshot: AccountSnapshot,
        open_orders: list[OpenOrder],
    ) -> None:
        with self._lock:
            self._lifecycle = AccountLifecycle.SNAPSHOT_LOADING
            self._state.snapshot = snapshot
            self._state.open_orders = list(open_orders)
            now = int(time.time() * 1000)
            self._state.last_reconciled_at_ms = now
            self._state.reconciliation_status = ReconciliationStatus.RECONCILED
            self._state.source = "rest_snapshot"
            self._lifecycle = AccountLifecycle.RECONCILED
            self._last_reason = "rest_snapshot_applied"
            self._version += 1

    def begin_live_streaming(self) -> None:
        with self._lock:
            if self._lifecycle == AccountLifecycle.RECONCILED:
                self._lifecycle = AccountLifecycle.LIVE_STREAMING
                self._last_reason = "live_streaming"
                self._version += 1

    def apply_private_event(self, event: dict[str, Any]) -> None:
        with self._lock:
            normalized = normalize_private_event(event)
            self._apply_normalized(normalized)

    def apply_normalized(self, event: NormalizedEvent) -> None:
        with self._lock:
            self._apply_normalized(event)

    def mark_stale(self, reason: str) -> None:
        with self._lock:
            self._lifecycle = AccountLifecycle.STALE
            self._state.reconciliation_status = ReconciliationStatus.STALE
            self._last_reason = reason
            self._version += 1

    def mark_unknown(self, reason: str) -> None:
        with self._lock:
            self._lifecycle = AccountLifecycle.UNKNOWN
            self._state.reconciliation_status = ReconciliationStatus.UNKNOWN
            self._last_reason = reason
            self._version += 1

    def mark_ws_disconnect(self) -> None:
        self.mark_stale("ws_disconnect")

    def mark_event_gap(self) -> None:
        self.mark_unknown("event_gap")

    def mark_rest_error(self) -> None:
        self.mark_unknown("rest_error")

    def mark_data_conflict(self, detail: str = "") -> None:
        with self._lock:
            self._lifecycle = AccountLifecycle.UNKNOWN
            self._state.reconciliation_status = ReconciliationStatus.DIVERGED
            self._last_reason = f"data_conflict:{detail}" if detail else "data_conflict"
            self._version += 1

    def requires_rest_resync(self) -> bool:
        with self._lock:
            return self._lifecycle in REQUIRES_REST_RESYNC

    def restart_clear(self) -> None:
        with self._lock:
            self._lifecycle = AccountLifecycle.UNINITIALIZED
            self._state = AccountState()
            self._seen_event_ids.clear()
            self._last_reason = "restart"
            self._version += 1

    def _apply_normalized(self, ev: NormalizedEvent) -> None:
        if ev.event_id in self._seen_event_ids:
            return
        self._seen_event_ids[ev.event_id] = None
        while len(self._seen_event_ids) > self._max_event_ids:
            oldest = next(iter(self._seen_event_ids))
            del self._seen_event_ids[oldest]

        if ev.event_type == NormalizedEventType.STREAM_TERMINATED:
            self._lifecycle = AccountLifecycle.STALE
            self._state.reconciliation_status = ReconciliationStatus.STALE
            self._last_reason = "stream_terminated"
            self._version += 1
            return

        if self._lifecycle in (
            AccountLifecycle.UNINITIALIZED,
            AccountLifecycle.SNAPSHOT_LOADING,
            AccountLifecycle.UNKNOWN,
        ):
            self._last_reason = "event_ignored_until_rest_baseline"
            return

        if ev.event_time_ms is not None:
            self._state.last_private_event_at_ms = ev.event_time_ms

        if ev.event_type == NormalizedEventType.ACCOUNT_POSITION:
            self._reduce_balances(ev)
        elif ev.event_type == NormalizedEventType.EXECUTION_REPORT:
            self._reduce_order(ev)

        if self._lifecycle == AccountLifecycle.RECONCILED:
            self._lifecycle = AccountLifecycle.LIVE_STREAMING
        self._state.source = "private_stream"
        self._version += 1

    def _reduce_balances(self, ev: NormalizedEvent) -> None:
        if not ev.balances:
            return
        existing: dict[str, Balance] = {}
        if self._state.snapshot is not None:
            for b in self._state.snapshot.balances:
                existing[b.asset] = b
        for asset, free, locked in ev.balances:
            existing[asset] = Balance(asset=asset, free=free, locked=locked)
        can_trade = True
        update_ms = ev.event_time_ms
        if self._state.snapshot is not None:
            can_trade = self._state.snapshot.can_trade
        self._state.snapshot = AccountSnapshot(
            balances=tuple(existing.values()),
            can_trade=can_trade,
            update_time_ms=update_ms,
            raw={},
        )

    def _reduce_order(self, ev: NormalizedEvent) -> None:
        if not ev.order_id:
            return
        status = (ev.order_status or "").upper()
        orders = {o.order_id: o for o in self._state.open_orders}
        if status in _TERMINAL_STATUSES:
            orders.pop(ev.order_id, None)
        else:
            prev = orders.get(ev.order_id)
            orders[ev.order_id] = OpenOrder(
                symbol=ev.symbol or (prev.symbol if prev else ""),
                order_id=ev.order_id,
                client_order_id=prev.client_order_id if prev else None,
                side=ev.side or (prev.side if prev else ""),
                order_type=prev.order_type if prev else "",
                price=ev.price or (prev.price if prev else "0"),
                orig_qty=ev.orig_qty or (prev.orig_qty if prev else "0"),
                executed_qty=ev.executed_qty or (prev.executed_qty if prev else "0"),
                status=status or (prev.status if prev else ""),
                symbol_type=prev.symbol_type if prev else None,
                raw=ev.raw or {},
            )
        self._state.open_orders = list(orders.values())


def detect_snapshot_conflict(
    rest_snapshot: AccountSnapshot,
    live_snapshot: Optional[AccountSnapshot],
    *,
    asset: str = "USDT",
    tolerance: float = 0.0,
) -> bool:
    if live_snapshot is None:
        return False

    def total(snap: AccountSnapshot, a: str) -> float:
        for b in snap.balances:
            if b.asset == a:
                return float(b.free) + float(b.locked)
        return 0.0

    return abs(total(rest_snapshot, asset) - total(live_snapshot, asset)) > tolerance
