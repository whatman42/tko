"""Decimal tick/lot/notional property tests."""
from __future__ import annotations

from decimal import Decimal

from src.python.exchange.models.instrument import LotSizeFilter, NotionalFilter, PriceFilter
from src.python.governance.market_structure.decimal_rules import (
    is_multiple_of,
    validate_notional,
    validate_price,
    validate_quantity,
)


def test_is_multiple_of_exact():
    assert is_multiple_of(Decimal("50000.00"), Decimal("0.01")) is True
    assert is_multiple_of(Decimal("50000.005"), Decimal("0.01")) is False
    assert is_multiple_of(Decimal("0.001"), Decimal("0.0001")) is True


def test_validate_price_boundaries():
    pf = PriceFilter("1", "100", "0.5")
    assert validate_price("10.0", pf) == []
    assert any("PRICE_FILTER" in x for x in validate_price("0.5", pf))
    assert any("PRICE_TICK" in x for x in validate_price("10.25", pf))


def test_validate_quantity_step():
    lot = LotSizeFilter("0.01", "10", "0.01")
    assert validate_quantity("0.05", lot) == []
    assert any("LOT_SIZE" in x for x in validate_quantity("0.015", lot))
    assert any("QTY_BELOW_MIN" in x for x in validate_quantity("0.001", lot))


def test_notional():
    nf = NotionalFilter(min_notional="10", max_notional="1000")
    assert any("NOTIONAL" in x for x in validate_notional("100", "0.05", nf))
    assert validate_notional("100", "0.2", nf) == []
