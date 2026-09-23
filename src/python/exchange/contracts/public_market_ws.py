"""P0 Contract: PublicMarketWS — real-time market data, fail-closed on stale.

LOCKED:
  - Subscribe / unsubscribe only
  - Stale / disconnect → MarketState = STALE → BLOCK execution path
  - Reconnect alone does NOT reopen execution gate
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional


class MarketConnectionState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class StreamSubscription:
    stream_name: str  # e.g. "btcusdt@depth"
    symbol: str
    stream_type: str  # depth | kline | trade | aggTrade | miniTicker


class PublicMarketWS(ABC):
    """Public market data WebSocket surface (no private/auth streams)."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def subscribe(self, streams: list[StreamSubscription]) -> None: ...

    @abstractmethod
    def unsubscribe(self, streams: list[StreamSubscription]) -> None: ...

    @abstractmethod
    def connection_state(self) -> MarketConnectionState: ...

    @abstractmethod
    def last_message_age_ms(self) -> Optional[int]:
        """Milliseconds since last valid message. None if never received."""
        ...

    def is_ready_for_execution(self, max_stale_ms: int = 5_000) -> bool:
        """Fail-closed: only CONNECTED + fresh data allows execution path."""
        if self.connection_state() != MarketConnectionState.CONNECTED:
            return False
        age = self.last_message_age_ms()
        if age is None or age > max_stale_ms:
            return False
        return True
