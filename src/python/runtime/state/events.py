"""Normalize private user-stream payloads into typed internal events. P1."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class NormalizedEventType(str, Enum):
    ACCOUNT_POSITION = "ACCOUNT_POSITION"
    EXECUTION_REPORT = "EXECUTION_REPORT"
    STREAM_TERMINATED = "STREAM_TERMINATED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class NormalizedEvent:
    event_type: NormalizedEventType
    event_time_ms: Optional[int]
    event_id: str
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    order_status: Optional[str] = None
    side: Optional[str] = None
    executed_qty: Optional[str] = None
    orig_qty: Optional[str] = None
    price: Optional[str] = None
    balances: tuple[tuple[str, str, str], ...] = ()
    raw: dict[str, Any] | None = None


def _event_body(msg: dict[str, Any]) -> dict[str, Any]:
    if "event" in msg and isinstance(msg["event"], dict):
        return msg["event"]
    if "data" in msg and isinstance(msg["data"], dict):
        data = msg["data"]
        if "e" in data:
            return data
        return data
    return msg


def normalize_private_event(msg: dict[str, Any]) -> NormalizedEvent:
    body = _event_body(msg)
    etype_raw = str(body.get("e") or body.get("event") or "")

    if etype_raw == "eventStreamTerminated":
        e_ms = body.get("E")
        return NormalizedEvent(
            event_type=NormalizedEventType.STREAM_TERMINATED,
            event_time_ms=int(e_ms) if e_ms is not None else None,
            event_id=f"term:{e_ms}",
            raw=dict(msg),
        )

    if etype_raw in ("outboundAccountPosition", "outboundAccountInfo", "balanceUpdate"):
        e_ms = body.get("E") or body.get("u")
        bals: list[tuple[str, str, str]] = []
        for b in body.get("B") or body.get("balances") or []:
            if not isinstance(b, dict):
                continue
            asset = str(b.get("a") or b.get("asset") or "")
            free = str(b.get("f") or b.get("free") or "0")
            locked = str(b.get("l") or b.get("locked") or "0")
            if asset:
                bals.append((asset, free, locked))
        eid = f"acct:{e_ms}:{len(bals)}"
        return NormalizedEvent(
            event_type=NormalizedEventType.ACCOUNT_POSITION,
            event_time_ms=int(e_ms) if e_ms is not None else None,
            event_id=eid,
            balances=tuple(bals),
            raw=dict(msg),
        )

    if etype_raw == "executionReport":
        e_ms = body.get("E")
        oid = str(body.get("i") or body.get("orderId") or "")
        trade_id = body.get("t")
        eid = f"exec:{oid}:{e_ms}:{trade_id}"
        return NormalizedEvent(
            event_type=NormalizedEventType.EXECUTION_REPORT,
            event_time_ms=int(e_ms) if e_ms is not None else None,
            event_id=eid,
            order_id=oid or None,
            symbol=str(body.get("s") or body.get("symbol") or "") or None,
            order_status=str(body.get("X") or body.get("status") or "") or None,
            side=str(body.get("S") or body.get("side") or "") or None,
            executed_qty=str(body.get("z") or body.get("executedQty") or "0"),
            orig_qty=str(body.get("q") or body.get("origQty") or "0"),
            price=str(body.get("p") or body.get("price") or "0"),
            raw=dict(msg),
        )

    e_ms = body.get("E")
    return NormalizedEvent(
        event_type=NormalizedEventType.UNKNOWN,
        event_time_ms=int(e_ms) if e_ms is not None else None,
        event_id=f"unk:{hash(str(sorted(body.items())) % 10_000_000)}:{e_ms}",
        raw=dict(msg),
    )
