"""P0 Contract: PrivateUserStream — listenToken only, type=1 only.

LOCKED:
  - Only POST /open/v1/user-listen-token + WS API subscribe.listenToken
  - symbolType != 1 → PRIVATE_WS_UNSUPPORTED → EXECUTION_BLOCKED
  - Token does NOT auto-renew
  - No legacy listenKey path
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional


class PrivateStreamState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    TOKEN_REQUESTED = "TOKEN_REQUESTED"
    SUBSCRIBED = "SUBSCRIBED"
    STALE = "STALE"
    TERMINATED = "TERMINATED"
    UNSUPPORTED = "UNSUPPORTED"  # e.g. symbolType=3
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ListenToken:
    token: str
    expiration_time_ms: int


class PrivateUserStream(ABC):
    """Private user data stream (account + order events). listenToken only."""

    @abstractmethod
    def create_listen_token(self, validity_ms: Optional[int] = None) -> ListenToken:
        """Call POST /open/v1/user-listen-token. Requires credentials."""
        ...

    @abstractmethod
    def subscribe(self, token: ListenToken) -> None:
        """Subscribe via WebSocket API userDataStream.subscribe.listenToken."""
        ...

    @abstractmethod
    def unsubscribe(self) -> None: ...

    @abstractmethod
    def stream_state(self) -> PrivateStreamState: ...

    @abstractmethod
    def is_supported_for_symbol_type(self, symbol_type: int) -> bool:
        """Must return True only for symbolType == 1 (MBX)."""
        ...

    def is_ready_for_execution(self) -> bool:
        """Fail-closed: only SUBSCRIBED state allows execution path."""
        return self.stream_state() == PrivateStreamState.SUBSCRIBED
