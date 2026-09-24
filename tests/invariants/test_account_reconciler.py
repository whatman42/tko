"""P1 AccountState reconciliation — unit + failure paths, no credentials."""
from __future__ import annotations

from src.python.exchange.contracts.account_state import ReconciliationStatus
from src.python.exchange.models.account import AccountSnapshot, Balance, OpenOrder
from src.python.runtime.state.lifecycle import AccountLifecycle
from src.python.runtime.state.reconciler import AccountReconciler
from src.python.runtime.state.store import InMemoryAccountStateStore


def _snap(*pairs: tuple[str, str, str]) -> AccountSnapshot:
    return AccountSnapshot(
        balances=tuple(Balance(a, f, l) for a, f, l in pairs),
        can_trade=True,
        update_time_ms=1,
    )


def _order(oid: str, status: str = "NEW") -> OpenOrder:
    return OpenOrder(
        symbol="BTC_USDT",
        order_id=oid,
        client_order_id=None,
        side="BUY",
        order_type="LIMIT",
        price="1",
        orig_qty="1",
        executed_qty="0",
        status=status,
    )


class FakeSource:
    def __init__(self) -> None:
        self.snapshot = _snap(("USDT", "100", "0"))
        self.orders: list[OpenOrder] = []
        self.fail = False

    def get_account_snapshot(self) -> AccountSnapshot:
        if self.fail:
            raise RuntimeError("rest_down")
        return self.snapshot

    def get_open_orders(self) -> list[OpenOrder]:
        if self.fail:
            raise RuntimeError("rest_down")
        return list(self.orders)


def test_uninitialized_balances_for_risk_are_none():
    store = InMemoryAccountStateStore()
    assert store.lifecycle() == AccountLifecycle.UNINITIALIZED
    assert store.balances_for_risk() is None
    assert store.get().is_ready_for_execution() is False


def test_full_resync_reconciles():
    store = InMemoryAccountStateStore()
    src = FakeSource()
    src.orders = [_order("1")]
    AccountReconciler(store, src).full_resync()
    assert store.lifecycle() == AccountLifecycle.RECONCILED
    assert store.get().reconciliation_status == ReconciliationStatus.RECONCILED
    assert store.balances_for_risk() is not None
    assert store.balances_for_risk()[0].free == "100"
    assert len(store.get().open_orders) == 1


def test_rest_error_marks_unknown_not_zero():
    store = InMemoryAccountStateStore()
    src = FakeSource()
    AccountReconciler(store, src).full_resync()
    src.fail = True
    try:
        AccountReconciler(store, src).full_resync()
        assert False
    except RuntimeError:
        pass
    assert store.lifecycle() == AccountLifecycle.UNKNOWN
    assert store.balances_for_risk() is None


def test_ws_disconnect_stale_requires_resync():
    store = InMemoryAccountStateStore()
    src = FakeSource()
    rec = AccountReconciler(store, src)
    rec.full_resync()
    store.begin_live_streaming()
    assert store.lifecycle() == AccountLifecycle.LIVE_STREAMING
    rec.on_ws_disconnect()
    assert store.lifecycle() == AccountLifecycle.STALE
    assert store.requires_rest_resync() is True
    assert store.balances_for_risk() is None


def test_reconnect_forces_full_resync():
    store = InMemoryAccountStateStore()
    src = FakeSource()
    rec = AccountReconciler(store, src)
    rec.full_resync()
    rec.on_ws_disconnect()
    src.snapshot = _snap(("USDT", "200", "0"))
    rec.on_ws_reconnected()
    assert store.lifecycle() == AccountLifecycle.RECONCILED
    assert store.balances_for_risk()[0].free == "200"


def test_restart_recovery():
    store = InMemoryAccountStateStore()
    src = FakeSource()
    AccountReconciler(store, src).full_resync()
    store.restart_clear()
    assert store.lifecycle() == AccountLifecycle.UNINITIALIZED
    assert store.get().snapshot is None
    assert store.balances_for_risk() is None
    AccountReconciler(store, src).full_resync()
    assert store.lifecycle() == AccountLifecycle.RECONCILED
