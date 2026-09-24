"""P1 event normalization, dedup, order lifecycle, balance reduce."""
from __future__ import annotations

from src.python.exchange.models.account import AccountSnapshot, Balance, OpenOrder
from src.python.runtime.state.events import NormalizedEventType, normalize_private_event
from src.python.runtime.state.lifecycle import AccountLifecycle
from src.python.runtime.state.store import InMemoryAccountStateStore


def _baseline(store: InMemoryAccountStateStore) -> None:
    store.apply_rest_snapshot(
        AccountSnapshot(balances=(Balance("USDT", "100", "10"), Balance("BTC", "1", "0"))),
        [
            OpenOrder(
                symbol="BTC_USDT",
                order_id="99",
                client_order_id="c",
                side="BUY",
                order_type="LIMIT",
                price="50000",
                orig_qty="0.1",
                executed_qty="0",
                status="NEW",
            )
        ],
    )
    store.begin_live_streaming()


def test_normalize_account_position():
    msg = {
        "e": "outboundAccountPosition",
        "E": 1000,
        "B": [{"a": "USDT", "f": "90", "l": "20"}],
    }
    ev = normalize_private_event(msg)
    assert ev.event_type == NormalizedEventType.ACCOUNT_POSITION
    assert ev.balances == (("USDT", "90", "20"),)


def test_normalize_execution_report():
    msg = {
        "e": "executionReport",
        "E": 2000,
        "s": "BTC_USDT",
        "i": 99,
        "X": "FILLED",
        "S": "BUY",
        "z": "0.1",
        "q": "0.1",
        "p": "50000",
        "t": 1,
    }
    ev = normalize_private_event(msg)
    assert ev.event_type == NormalizedEventType.EXECUTION_REPORT
    assert ev.order_id == "99"
    assert ev.order_status == "FILLED"


def test_normalize_stream_terminated():
    ev = normalize_private_event({"e": "eventStreamTerminated", "E": 3})
    assert ev.event_type == NormalizedEventType.STREAM_TERMINATED


def test_duplicate_event_idempotent():
    store = InMemoryAccountStateStore()
    _baseline(store)
    msg = {
        "e": "outboundAccountPosition",
        "E": 1000,
        "B": [{"a": "USDT", "f": "50", "l": "0"}],
    }
    store.apply_private_event(msg)
    v1 = store.version()
    store.apply_private_event(msg)
    bals2 = store.get().snapshot.balances
    usdt = {b.asset: b for b in bals2}["USDT"]
    assert usdt.free == "50"


def test_balance_reduce_merges_assets():
    store = InMemoryAccountStateStore()
    _baseline(store)
    store.apply_private_event(
        {
            "e": "outboundAccountPosition",
            "E": 5,
            "B": [{"a": "USDT", "f": "80", "l": "5"}],
        }
    )
    by = {b.asset: b for b in store.get().snapshot.balances}
    assert by["USDT"].free == "80"
    assert by["BTC"].free == "1"


def test_order_filled_removes_from_open():
    store = InMemoryAccountStateStore()
    _baseline(store)
    assert len(store.get().open_orders) == 1
    store.apply_private_event(
        {
            "e": "executionReport",
            "E": 9,
            "s": "BTC_USDT",
            "i": 99,
            "X": "FILLED",
            "S": "BUY",
            "z": "0.1",
            "q": "0.1",
            "p": "50000",
            "t": 7,
        }
    )
    assert store.get().open_orders == []


def test_order_partial_updates_book():
    store = InMemoryAccountStateStore()
    _baseline(store)
    store.apply_private_event(
        {
            "e": "executionReport",
            "E": 10,
            "s": "BTC_USDT",
            "i": 99,
            "X": "PARTIALLY_FILLED",
            "S": "BUY",
            "z": "0.05",
            "q": "0.1",
            "p": "50000",
            "t": 8,
        }
    )
    o = store.get().open_orders[0]
    assert o.executed_qty == "0.05"
    assert o.status == "PARTIALLY_FILLED"


def test_stream_terminated_marks_stale():
    store = InMemoryAccountStateStore()
    _baseline(store)
    store.apply_private_event({"e": "eventStreamTerminated", "E": 99})
    assert store.lifecycle() == AccountLifecycle.STALE
    assert store.balances_for_risk() is None


def test_events_before_baseline_ignored_for_balances():
    store = InMemoryAccountStateStore()
    store.apply_private_event(
        {
            "e": "outboundAccountPosition",
            "E": 1,
            "B": [{"a": "USDT", "f": "999", "l": "0"}],
        }
    )
    assert store.get().snapshot is None
    assert store.lifecycle() == AccountLifecycle.UNINITIALIZED
