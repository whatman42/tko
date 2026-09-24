"""Private User Stream — listenToken only, symbolType=1 only. P0.4."""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable, Optional

from src.python.exchange.contracts.private_user_stream import (
    ListenToken,
    PrivateStreamState,
    PrivateUserStream,
)
from src.python.exchange.tokocrypto.rest.auth import Credentials, build_signed_params

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore

try:
    import websockets.sync.client as ws_sync
except ImportError:  # pragma: no cover
    ws_sync = None  # type: ignore

REST_BASE = "https://www.tokocrypto.com"
WS_API_BASE = "wss://ws-api.tokocrypto.site:443/ws-api/v3"


class TokocryptoPrivateUserStream(PrivateUserStream):
    """listenToken path only. is_supported_for_symbol_type(3) → False."""

    def __init__(
        self,
        credentials: Optional[Credentials] = None,
        *,
        rest_base: str = REST_BASE,
        ws_api_base: str = WS_API_BASE,
        on_event: Optional[Callable[[dict[str, Any]], None]] = None,
        transport: Optional[Any] = None,
    ) -> None:
        self._creds = credentials
        self._rest_base = rest_base.rstrip("/")
        self._ws_api_base = ws_api_base
        self._on_event = on_event
        self._transport = transport
        self._state = PrivateStreamState.DISCONNECTED
        self._token: Optional[ListenToken] = None
        self._ws: Any = None
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._recv_thread: Optional[threading.Thread] = None
        self._subscription_id: Optional[int] = None

    def is_supported_for_symbol_type(self, symbol_type: int) -> bool:
        return symbol_type == 1

    def create_listen_token(self, validity_ms: Optional[int] = None) -> ListenToken:
        if httpx is None:
            raise RuntimeError("httpx required")
        if self._creds is None or not self._creds.is_present():
            raise RuntimeError("credentials required for listenToken")
        params: dict[str, Any] = {}
        if validity_ms is not None:
            params["validity"] = validity_ms
        signed = build_signed_params(self._creds.api_secret, params)
        headers = {"X-MBX-APIKEY": self._creds.api_key}
        with self._lock:
            self._state = PrivateStreamState.TOKEN_REQUESTED
        client_kwargs: dict[str, Any] = {"timeout": 15.0}
        if self._transport is not None:
            client_kwargs["transport"] = self._transport
        with httpx.Client(**client_kwargs) as client:
            r = client.post(
                f"{self._rest_base}/open/v1/user-listen-token",
                data=signed,
                headers=headers,
            )
            r.raise_for_status()
            body = r.json()
        if not isinstance(body, dict) or body.get("code") not in (0, "0", None):
            with self._lock:
                self._state = PrivateStreamState.UNKNOWN
            raise RuntimeError(f"listenToken failed: {body}")
        data = body.get("data") or {}
        token = ListenToken(
            token=str(data.get("token") or ""),
            expiration_time_ms=int(data.get("expirationTime") or 0),
        )
        if not token.token:
            raise RuntimeError("listenToken empty in response")
        with self._lock:
            self._token = token
        return token

    def subscribe(self, token: ListenToken) -> None:
        if ws_sync is None:
            raise RuntimeError("websockets package required")
        with self._lock:
            self._token = token
            self._stop.clear()
        try:
            self._ws = ws_sync.connect(self._ws_api_base, close_timeout=5)
            payload = {
                "id": f"sub-{int(time.time())}",
                "method": "userDataStream.subscribe.listenToken",
                "params": {"listenToken": token.token},
            }
            self._ws.send(json.dumps(payload))
            with self._lock:
                self._state = PrivateStreamState.SUBSCRIBED
            self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
            self._recv_thread.start()
        except Exception:
            with self._lock:
                self._state = PrivateStreamState.DISCONNECTED
            raise

    def unsubscribe(self) -> None:
        with self._lock:
            self._stop.set()
            if self._ws is not None:
                try:
                    unsub = {
                        "id": f"unsub-{int(time.time())}",
                        "method": "userDataStream.unsubscribe",
                    }
                    if self._subscription_id is not None:
                        unsub["params"] = {"subscriptionId": self._subscription_id}
                    self._ws.send(json.dumps(unsub))
                except Exception:
                    pass
                try:
                    self._ws.close()
                except Exception:
                    pass
            self._ws = None
            self._state = PrivateStreamState.DISCONNECTED
            self._token = None

    def stream_state(self) -> PrivateStreamState:
        with self._lock:
            return self._state

    def force_state(self, state: PrivateStreamState) -> None:
        with self._lock:
            self._state = state

    def mark_unsupported(self) -> None:
        with self._lock:
            self._state = PrivateStreamState.UNSUPPORTED

    def _recv_loop(self) -> None:
        while not self._stop.is_set():
            try:
                if self._ws is None:
                    break
                raw = self._ws.recv(timeout=1.0)
                msg = json.loads(raw) if isinstance(raw, str) else raw
                if not isinstance(msg, dict):
                    continue
                if "subscriptionId" in msg:
                    with self._lock:
                        self._subscription_id = int(msg["subscriptionId"])
                event = msg.get("event") if isinstance(msg.get("event"), dict) else msg
                if isinstance(event, dict) and event.get("e") == "eventStreamTerminated":
                    with self._lock:
                        self._state = PrivateStreamState.TERMINATED
                    break
                if self._on_event:
                    self._on_event(msg)
            except Exception:
                if self._stop.is_set():
                    break
                with self._lock:
                    if self._state == PrivateStreamState.SUBSCRIBED:
                        self._state = PrivateStreamState.DISCONNECTED
                break
