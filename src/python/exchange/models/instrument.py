"""Shared instrument metadata models for P0."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Optional


class SymbolType(IntEnum):
    MBX = 1
    # type 2 historically existed; treat as unknown if seen
    NEXTME = 3


@dataclass(frozen=True)
class PriceFilter:
    min_price: str
    max_price: str
    tick_size: str


@dataclass(frozen=True)
class LotSizeFilter:
    min_qty: str
    max_qty: str
    step_size: str


@dataclass(frozen=True)
class NotionalFilter:
    min_notional: Optional[str] = None
    max_notional: Optional[str] = None


@dataclass(frozen=True)
class InstrumentMeta:
    symbol: str
    base_asset: str
    quote_asset: str
    symbol_type: Optional[int]
    status: str
    base_precision: int
    quote_precision: int
    price_filter: Optional[PriceFilter] = None
    lot_size: Optional[LotSizeFilter] = None
    market_lot_size: Optional[LotSizeFilter] = None
    notional: Optional[NotionalFilter] = None
    raw: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    @property
    def is_mbx(self) -> bool:
        return self.symbol_type == SymbolType.MBX

    @property
    def is_nextme(self) -> bool:
        return self.symbol_type == SymbolType.NEXTME
