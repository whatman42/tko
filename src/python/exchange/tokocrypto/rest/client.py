"""Tokocrypto REST client — P0.1 foundation. Read-only. No create_order."""
from __future__ import annotations

import os
from typing import Any, Mapping, Optional

import httpx

from src.python.exchange.contracts.exchange_client import AbstractExchangeClient
from src.python.exchange.models.account import AccountSnapshot, OpenOrder
from src.python.exchange.models.instrument import InstrumentMeta
from src.python.exchange.tokocrypto.rest.auth import (
    Credentials,
    build_signed_params,
)
from src.python.exchange.tokocrypto.rest.parsers import (
    parse_account_snapshot,
    parse_open_orders,
    parse_server_time,
    parse_symbols_response,
)

DEFAULT_REST_BASE = "https://www.tokocrypto.com"


class TokocryptoRestClient(AbstractExchangeClient):
    """Concrete ExchangeClient. Credentials optional for public methods only."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_REST_BASE,
        credentials: Optional[Credentials] = None,
        timeout_s: float = 15.0,
        recv_window: int = 5000,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._creds = credentials
        self._recv_window = recv_window
        self._client = httpx.Client(
            base_url=self._base,
            timeout=timeout_s,
            transport=transport,
            headers={"Accept": "application/json", "User-Agent": "tko-p0/0.1"},
        )

    @classmethod
    def from_env(cls, **kwargs: Any) -> "TokocryptoRestClient":
        creds: Optional[Credentials] = None
        if os.environ.get("TOKOCRYPTO_API_KEY") and os.environ.get("TOKOCRYPTO_API_SECRET"):
            creds = Credentials.from_env()
        return cls(credentials=creds, **kwargs)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "TokocryptoRestClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def get_server_time(self) -> int:
        r = self._client.get("/open/v1/common/time")
        r.raise_for_status()
        return parse_server_time(r.json())

    def get_symbols(self) -> list[InstrumentMeta]:
        r = self._client.get("/open/v1/common/symbols")
        r.raise_for_status()
        return parse_symbols_response(r.json())

    def _require_creds(self) -> Credentials:
        if self._creds is None or not self._creds.is_present():
            raise RuntimeError(
                "SIGNED endpoint requires TOKOCRYPTO_API_KEY / TOKOCRYPTO_API_SECRET"
            )
        return self._creds

    def _signed_get(self, path: str, params: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
        creds = self._require_creds()
        signed = build_signed_params(creds.api_secret, params, recv_window=self._recv_window)
        headers = {"X-MBX-APIKEY": creds.api_key}
        r = self._client.get(path, params=signed, headers=headers)
        r.raise_for_status()
        body = r.json()
        if isinstance(body, dict) and body.get("code") not in (None, 0, "0"):
            raise RuntimeError(f"Tokocrypto API error code={body.get('code')} msg={body.get('msg')}")
        return body if isinstance(body, dict) else {"data": body}

    def get_account_snapshot(self) -> AccountSnapshot:
        body = self._signed_get("/open/v1/account/spot")
        return parse_account_snapshot(body)

    def get_open_orders(self) -> list[OpenOrder]:
        body = self._signed_get("/open/v1/orders")
        return parse_open_orders(body)
