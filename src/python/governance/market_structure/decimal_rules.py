"""Deterministic price/qty rules using Decimal — no silent rounding."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Optional

from src.python.exchange.models.instrument import (
    InstrumentMeta,
    LotSizeFilter,
    NotionalFilter,
    PriceFilter,
)


class ValidationError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _d(value: str | Decimal) -> Decimal:
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as e:
        raise ValidationError("PRECISION", f"invalid decimal: {value!r}") from e


def is_multiple_of(value: Decimal, step: Decimal) -> bool:
    if step == 0:
        return False
    q = value / step
    return q == q.to_integral_value()


def validate_price(price: str, pf: Optional[PriceFilter]) -> list[str]:
    failures: list[str] = []
    if pf is None:
        failures.append("METADATA_MISSING:price_filter")
        return failures
    p = _d(price)
    min_p = _d(pf.min_price)
    max_p = _d(pf.max_price)
    tick = _d(pf.tick_size)
    if p < min_p or (max_p > 0 and p > max_p):
        failures.append(f"PRICE_FILTER:price={p} not in [{min_p},{max_p}]")
    if tick > 0 and not is_multiple_of(p, tick):
        failures.append(f"PRICE_TICK:price={p} not multiple of tick={tick}")
    return failures


def validate_quantity(
    qty: str,
    lot: Optional[LotSizeFilter],
    *,
    market: bool = False,
    market_lot: Optional[LotSizeFilter] = None,
) -> list[str]:
    failures: list[str] = []
    rule = market_lot if market and market_lot is not None else lot
    if rule is None:
        failures.append("METADATA_MISSING:lot_size")
        return failures
    q = _d(qty)
    min_q = _d(rule.min_qty)
    max_q = _d(rule.max_qty)
    step = _d(rule.step_size)
    if q < min_q:
        failures.append(f"QTY_BELOW_MIN:qty={q} < min={min_q}")
    if max_q > 0 and q > max_q:
        failures.append(f"QTY_ABOVE_MAX:qty={q} > max={max_q}")
    if step > 0 and not is_multiple_of(q, step):
        failures.append(f"LOT_SIZE:qty={q} not multiple of step={step}")
    return failures


def validate_notional(
    price: str,
    qty: str,
    nf: Optional[NotionalFilter],
) -> list[str]:
    failures: list[str] = []
    if nf is None or (nf.min_notional is None and nf.max_notional is None):
        return failures
    notional = _d(price) * _d(qty)
    if nf.min_notional is not None and notional < _d(nf.min_notional):
        failures.append(f"NOTIONAL:notional={notional} < min={nf.min_notional}")
    if nf.max_notional is not None and notional > _d(nf.max_notional):
        failures.append(f"NOTIONAL:notional={notional} > max={nf.max_notional}")
    return failures


def validate_precision_strings(price: str, qty: str) -> list[str]:
    failures: list[str] = []
    for label, v in (("price", price), ("quantity", qty)):
        try:
            Decimal(str(v))
        except (InvalidOperation, ValueError):
            failures.append(f"PRECISION:invalid_{label}={v!r}")
            continue
        s = str(v).lower()
        if "e" in s:
            failures.append(f"PRECISION:scientific_notation_{label}={v!r}")
    return failures


def floor_to_step_display_only(value: str, step: str) -> str:
    """Display helper only — MUST NOT be used to auto-fix order intent."""
    v = _d(value)
    s = _d(step)
    if s <= 0:
        return str(v)
    n = (v / s).to_integral_value(rounding=ROUND_DOWN)
    return str(n * s)
