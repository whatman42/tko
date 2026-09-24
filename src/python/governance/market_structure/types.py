"""P2 gate outcomes and order intent (validation only — no submission)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GateVerdict(str, Enum):
    PASS = "PASS"
    BLOCK = "BLOCK"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"


class BlockReason(str, Enum):
    NONE = "NONE"
    SYMBOL_NOT_FOUND = "SYMBOL_NOT_FOUND"
    SYMBOL_TYPE_NOT_EXECUTABLE = "SYMBOL_TYPE_NOT_EXECUTABLE"
    INSTRUMENT_NOT_TRADING = "INSTRUMENT_NOT_TRADING"
    MARKET_STALE = "MARKET_STALE"
    MARKET_DISCONNECTED = "MARKET_DISCONNECTED"
    MARKET_UNKNOWN = "MARKET_UNKNOWN"
    PRICE_FILTER = "PRICE_FILTER"
    PRICE_TICK = "PRICE_TICK"
    LOT_SIZE = "LOT_SIZE"
    QTY_BELOW_MIN = "QTY_BELOW_MIN"
    QTY_ABOVE_MAX = "QTY_ABOVE_MAX"
    NOTIONAL = "NOTIONAL"
    PRECISION = "PRECISION"
    METADATA_STALE = "METADATA_STALE"
    METADATA_MISSING = "METADATA_MISSING"
    INVALID_INTENT = "INVALID_INTENT"


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: str
    price: str
    quantity: str
    order_type: str = "LIMIT"


@dataclass(frozen=True)
class GateResult:
    verdict: GateVerdict
    reason: BlockReason
    detail: str = ""
    symbol: str = ""
    checks: tuple[str, ...] = field(default_factory=tuple)

    @property
    def allow(self) -> bool:
        return self.verdict == GateVerdict.PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "reason": self.reason.value,
            "detail": self.detail,
            "symbol": self.symbol,
            "checks": list(self.checks),
            "allow": self.allow,
        }
