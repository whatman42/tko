"""Market data health for P2 gate."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.python.exchange.contracts.public_market_ws import MarketConnectionState


class MarketHealth(str, Enum):
    OK = "OK"
    STALE = "STALE"
    DISCONNECTED = "DISCONNECTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class MarketState:
    connection: MarketConnectionState = MarketConnectionState.DISCONNECTED
    last_message_age_ms: Optional[int] = None
    max_stale_ms: int = 5_000
    metadata_age_ms: Optional[int] = None
    max_metadata_age_ms: int = 86_400_000

    def health(self) -> MarketHealth:
        if self.connection == MarketConnectionState.DISCONNECTED:
            return MarketHealth.DISCONNECTED
        if self.connection == MarketConnectionState.UNKNOWN:
            return MarketHealth.UNKNOWN
        if self.connection == MarketConnectionState.STALE:
            return MarketHealth.STALE
        if self.connection == MarketConnectionState.CONNECTING:
            return MarketHealth.UNKNOWN
        if self.last_message_age_ms is None:
            return MarketHealth.UNKNOWN
        if self.last_message_age_ms > self.max_stale_ms:
            return MarketHealth.STALE
        return MarketHealth.OK

    def metadata_ok(self) -> bool:
        if self.metadata_age_ms is None:
            return True
        return self.metadata_age_ms <= self.max_metadata_age_ms
