"""Parse Tokocrypto REST payloads into P0 models. No side effects."""
from __future__ import annotations

from typing import Any

from src.python.exchange.models.account import AccountSnapshot, Balance, OpenOrder
from src.python.exchange.models.instrument import (
    InstrumentMeta,
    LotSizeFilter,
    NotionalFilter,
    PriceFilter,
)


def _filter_by_type(filters: list[dict[str, Any]], ftype: str) -> dict[str, Any] | None:
    for f in filters or []:
        if f.get("filterType") == ftype:
            return f
    return None


def parse_instrument(raw: dict[str, Any]) -> InstrumentMeta:
    """Map one symbol object from /open/v1/common/symbols into InstrumentMeta."""
    filters = raw.get("filters") or []
    pf = _filter_by_type(filters, "PRICE_FILTER")
    ls = _filter_by_type(filters, "LOT_SIZE")
    mls = _filter_by_type(filters, "MARKET_LOT_SIZE")
    nf = _filter_by_type(filters, "NOTIONAL") or _filter_by_type(filters, "MIN_NOTIONAL")

    symbol_type = raw.get("type")
    if symbol_type is None:
        symbol_type = raw.get("symbolType")
    try:
        symbol_type_int = int(symbol_type) if symbol_type is not None else None
    except (TypeError, ValueError):
        symbol_type_int = None

    return InstrumentMeta(
        symbol=str(raw.get("symbol") or ""),
        base_asset=str(raw.get("baseAsset") or raw.get("base_asset") or ""),
        quote_asset=str(raw.get("quoteAsset") or raw.get("quote_asset") or ""),
        symbol_type=symbol_type_int,
        status=str(raw.get("status") or raw.get("symbolStatus") or "UNKNOWN"),
        base_precision=int(raw.get("basePrecision") or raw.get("baseAssetPrecision") or 8),
        quote_precision=int(raw.get("quotePrecision") or raw.get("quoteAssetPrecision") or 8),
        price_filter=PriceFilter(
            min_price=str(pf.get("minPrice", "0")),
            max_price=str(pf.get("maxPrice", "0")),
            tick_size=str(pf.get("tickSize", "0")),
        )
        if pf
        else None,
        lot_size=LotSizeFilter(
            min_qty=str(ls.get("minQty", "0")),
            max_qty=str(ls.get("maxQty", "0")),
            step_size=str(ls.get("stepSize", "0")),
        )
        if ls
        else None,
        market_lot_size=LotSizeFilter(
            min_qty=str(mls.get("minQty", "0")),
            max_qty=str(mls.get("maxQty", "0")),
            step_size=str(mls.get("stepSize", "0")),
        )
        if mls
        else None,
        notional=NotionalFilter(
            min_notional=str(nf.get("minNotional")) if nf and nf.get("minNotional") is not None else None,
            max_notional=str(nf.get("maxNotional")) if nf and nf.get("maxNotional") is not None else None,
        )
        if nf
        else None,
        raw=dict(raw),
    )


def parse_symbols_response(payload: dict[str, Any]) -> list[InstrumentMeta]:
    """Accept various shapes: {code, data: [...]} or {data: {list: [...]}} or bare list."""
    data = payload.get("data", payload)
    if isinstance(data, dict):
        data = data.get("list") or data.get("symbols") or data.get("symbolList") or []
    if not isinstance(data, list):
        return []
    return [parse_instrument(item) for item in data if isinstance(item, dict)]


def parse_server_time(payload: dict[str, Any]) -> int:
    data = payload.get("data", payload)
    if isinstance(data, dict):
        for key in ("serverTime", "time", "timestamp"):
            if key in data:
                return int(data[key])
    if "serverTime" in payload:
        return int(payload["serverTime"])
    if "timestamp" in payload:
        return int(payload["timestamp"])
    raise ValueError("server time field not found in response")


def parse_account_snapshot(payload: dict[str, Any]) -> AccountSnapshot:
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        data = {}
    balances_raw = data.get("balances") or data.get("assets") or []
    balances: list[Balance] = []
    for b in balances_raw:
        if not isinstance(b, dict):
            continue
        asset = str(b.get("asset") or b.get("a") or "")
        free = str(b.get("free") or b.get("f") or "0")
        locked = str(b.get("locked") or b.get("l") or "0")
        if asset:
            balances.append(Balance(asset=asset, free=free, locked=locked))
    can_trade = bool(data.get("canTrade", data.get("T", True)))
    update_ms = data.get("updateTime") or data.get("u")
    return AccountSnapshot(
        balances=tuple(balances),
        can_trade=can_trade,
        update_time_ms=int(update_ms) if update_ms is not None else None,
        raw=dict(data) if isinstance(data, dict) else {},
    )


def parse_open_orders(payload: dict[str, Any]) -> list[OpenOrder]:
    data = payload.get("data", payload)
    if isinstance(data, dict):
        data = data.get("list") or data.get("orders") or []
    if not isinstance(data, list):
        return []
    orders: list[OpenOrder] = []
    for o in data:
        if not isinstance(o, dict):
            continue
        st = o.get("symbolType") or o.get("type")
        try:
            st_int = int(st) if st is not None else None
        except (TypeError, ValueError):
            st_int = None
        orders.append(
            OpenOrder(
                symbol=str(o.get("symbol") or ""),
                order_id=str(o.get("orderId") or o.get("bOrderId") or o.get("i") or ""),
                client_order_id=(
                    str(o["clientId"]) if o.get("clientId") is not None else None
                ),
                side=str(o.get("side") or o.get("S") or ""),
                order_type=str(o.get("type") or o.get("o") or ""),
                price=str(o.get("price") or o.get("p") or "0"),
                orig_qty=str(o.get("origQty") or o.get("quantity") or o.get("q") or "0"),
                executed_qty=str(o.get("executedQty") or o.get("z") or "0"),
                status=str(o.get("status") or o.get("X") or ""),
                symbol_type=st_int,
                raw=dict(o),
            )
        )
    return orders
