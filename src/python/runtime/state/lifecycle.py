"""Account reconciliation lifecycle phases — P1 state machine."""
from __future__ import annotations

from enum import Enum


class AccountLifecycle(str, Enum):
    UNINITIALIZED = "UNINITIALIZED"
    SNAPSHOT_LOADING = "SNAPSHOT_LOADING"
    RECONCILED = "RECONCILED"
    LIVE_STREAMING = "LIVE_STREAMING"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


REQUIRES_REST_RESYNC = frozenset(
    {
        AccountLifecycle.STALE,
        AccountLifecycle.UNKNOWN,
        AccountLifecycle.UNINITIALIZED,
        AccountLifecycle.SNAPSHOT_LOADING,
    }
)
