"""Invariant: AccountState blocks execution unless RECONCILED."""
from __future__ import annotations

from src.python.exchange.contracts.account_state import AccountState, ReconciliationStatus
from src.python.exchange.models.account import AccountSnapshot, Balance


def test_uninitialized_account_state_not_ready():
    state = AccountState()
    assert state.is_ready_for_execution() is False
    assert state.reconciliation_status == ReconciliationStatus.UNKNOWN


def test_reconciled_with_snapshot_is_ready():
    snap = AccountSnapshot(
        balances=(Balance(asset="USDT", free="1000", locked="0"),),
        can_trade=True,
    )
    state = AccountState(
        snapshot=snap,
        reconciliation_status=ReconciliationStatus.RECONCILED,
        last_reconciled_at_ms=1_700_000_000_000,
    )
    assert state.is_ready_for_execution() is True


def test_reconciled_without_snapshot_not_ready():
    state = AccountState(
        snapshot=None,
        reconciliation_status=ReconciliationStatus.RECONCILED,
    )
    assert state.is_ready_for_execution() is False


def test_stale_or_diverged_not_ready():
    snap = AccountSnapshot(balances=())
    for status in (
        ReconciliationStatus.UNKNOWN,
        ReconciliationStatus.IN_PROGRESS,
        ReconciliationStatus.DIVERGED,
        ReconciliationStatus.STALE,
    ):
        state = AccountState(snapshot=snap, reconciliation_status=status)
        assert state.is_ready_for_execution() is False, status
