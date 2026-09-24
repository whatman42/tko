"""UNKNOWN / STALE never treated as zero for risk."""
from __future__ import annotations

from src.python.exchange.models.account import AccountSnapshot, Balance
from src.python.exchange.tokocrypto.execution_readiness import (
    EXECUTION_ENABLEMENT,
    evaluate_execution_readiness,
)
from src.python.exchange.contracts.symbol_router import ExecutionEligibility, RouteResult
from src.python.runtime.state.lifecycle import AccountLifecycle
from src.python.runtime.state.store import InMemoryAccountStateStore


def test_execution_still_blocked_after_reconcile():
    assert EXECUTION_ENABLEMENT == "BLOCKED"
    store = InMemoryAccountStateStore()
    store.apply_rest_snapshot(
        AccountSnapshot(balances=(Balance("USDT", "1", "0"),)),
        [],
    )
    route = RouteResult(
        symbol="BTC_USDT",
        symbol_type=1,
        eligibility=ExecutionEligibility.ELIGIBLE_FOR_EXECUTION,
        rest_base="x",
        public_ws_base="y",
        private_ws_supported=True,
        reason="ok",
    )
    report = evaluate_execution_readiness(route=route, account=store.get())
    assert report.ready is False
    assert "EXECUTION_ENABLEMENT=BLOCKED" in report.reasons


def test_unknown_not_zero():
    store = InMemoryAccountStateStore()
    store.apply_rest_snapshot(
        AccountSnapshot(balances=(Balance("USDT", "500", "0"),)),
        [],
    )
    store.mark_unknown("gap")
    assert store.lifecycle() == AccountLifecycle.UNKNOWN
    assert store.balances_for_risk() is None
    st = store.get()
    assert st.snapshot is not None
    assert st.snapshot.balances[0].free == "500"
    assert st.is_ready_for_execution() is False


def test_data_conflict_marks_diverged_then_resync_heals():
    store = InMemoryAccountStateStore()
    store.apply_rest_snapshot(
        AccountSnapshot(balances=(Balance("USDT", "100", "0"),)),
        [],
    )
    store.mark_data_conflict("usdt_mismatch")
    assert store.get().reconciliation_status.value == "DIVERGED"
    assert store.balances_for_risk() is None
    store.apply_rest_snapshot(
        AccountSnapshot(balances=(Balance("USDT", "100", "0"),)),
        [],
    )
    assert store.lifecycle() == AccountLifecycle.RECONCILED
    assert store.balances_for_risk() is not None
