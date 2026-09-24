"""Public Market WS — P0.3. Fail-closed on disconnect/stale. No order authority."""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable, Optional

from src.python.exchange.contracts.public_market_ws import (
    MarketConnectionState,
    PublicMarketWS,
    StreamSubscription,
)

try:
    import websockets.sync.client as ws_sync
except ImportError:  # pragma: no cover
    ws_sync = None  # type: ignore


def stream_name_for_mbx(symbol: str, stream_type: str, interval: str | None = None) -> str:
    base = symbol.replace("_", "").replace("-", "").lower()
    if stream_type == "kline" and interval:
        return f"{base}@kline_{interval}"
    return f"{base}@{stream_type}"


class TokocryptoPublicMarketWS(PublicMarketWS):
    def __init__(
        self,
        *,
        ws_base: str = "wss://stream-cloud.tokocrypto.site/stream",
        stale_after_ms: int = 5_000,
        on_message: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> None:
        self._ws_base = ws_base.rstrip("/")
        self._stale_after_ms = stale_after_ms
        self._on_message = on_message
        self._state = MarketConnectionState.DISCONNECTED
        self._last_msg_ms: Optional[int] = None
        self._subscriptions: list[StreamSubscription] = []
        self._ws: Any = None
        self._lock = threading.RLock()
        self._recv_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def connect(self) -> None:
        with self._lock:
            if ws_sync is None:
                raise RuntimeError("websockets package required for PublicMarketWS")
            self._state = MarketConnectionState.CONNECTING
            url = f"{self._ws_base}"
            if not url.startswith("ws"):
                raise ValueError(f"invalid ws base: {url}")
            try:
                self._ws = ws_sync.connect(url, close_timeout=5)
                self._state = MarketConnectionState.CONNECTED
                self._stop.clear()
                self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
                self._recv_thread.start()
            except Exception:
                self._state = MarketConnectionState.DISCONNECTED
                self._ws = None
                raise

    def disconnect(self) -> None:
        with self._lock:
            self._stop.set()
            if self._ws is not None:
                try:
                    self._ws.close()
                except Exception:
                    pass
            self._ws = None
            self._state = MarketConnectionState.DISCONNECTED
            self._last_msg_ms = None

    def subscribe(self, streams: list[StreamSubscription]) -> None:
        with self._lock:
            if self._state != MarketConnectionState.CONNECTED or self._ws is None:
                raise RuntimeError("not connected")
            names = [s.stream_name for s in streams]
            payload = {"method": "SUBSCRIBE", "params": names, "id": int(time.time() * 1000) % 1_000_000}
            self._ws.send(json.dumps(payload))
            self._subscriptions.extend(streams)

    def unsubscribe(self, streams: list[StreamSubscription]) -> None:
        with self._lock:
            if self._state != MarketConnectionState.CONNECTED or self._ws is None:
                return
            names = [s.stream_name for s in streams]
            payload = {"method": "UNSUBSCRIBE", "params": names, "id": int(time.time() * 1000) % 1_000_000}
            try:
                self._ws.send(json.dumps(payload))
            except Exception:
                pass
            drop = {s.stream_name for s in streams}
            self._subscriptions = [s for s in self._subscriptions if s.stream_name not in drop]

    def connection_state(self) -> MarketConnectionState:
        with self._lock:
            if self._state == MarketConnectionState.CONNECTED:
                age = self.last_message_age_ms()
                if age is not None and age > self._stale_after_ms:
                    return MarketConnectionState.STALE
            return self._state

    def last_message_age_ms(self) -> Optional[int]:
        with self._lock:
            if self._last_msg_ms is None:
                return None
            return int(time.time() * 1000) - self._last_msg_ms

    def mark_message_received(self) -> None:
        with self._lock:
            self._last_msg_ms = int(time.time() * 1000)
            if self._state == MarketConnectionState.STALE:
                self._state = MarketConnectionState.CONNECTED

    def force_state(self, state: MarketConnectionState) -> None:
        with self._lock:
            self._state = state
            if state == MarketConnectionState.DISCONNECTED:
                self._last_msg_ms = None

    def _recv_loop(self) -> None:
        while not self._stop.is_set():
            try:
                if self._ws is None:
                    break
                raw = self._ws.recv(timeout=1.0)
                with self._lock:
                    self._last_msg_ms = int(time.time() * 1000)
                    if self._state == MarketConnectionState.STALE:
                        self._state = MarketConnectionState.CONNECTED
                if self._on_message:
                    try:
                        msg = json.loads(raw) if isinstance(raw, str) else raw
                        if isinstance(msg, dict):
                            self._on_message(msg)
                    except Exception:
                        pass
            except Exception:
                if self._stop.is_set():
                    break
                with self._lock:
                    self._state = MarketConnectionState.DISCONNECTED
                break
