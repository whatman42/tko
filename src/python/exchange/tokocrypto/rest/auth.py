"""HMAC-SHA256 signing for Tokocrypto SIGNED endpoints. Credentials from env only."""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from typing import Mapping, Optional
from urllib.parse import urlencode


@dataclass(frozen=True)
class Credentials:
    api_key: str
    api_secret: str

    @classmethod
    def from_env(cls) -> "Credentials":
        key = os.environ.get("TOKOCRYPTO_API_KEY", "").strip()
        secret = os.environ.get("TOKOCRYPTO_API_SECRET", "").strip()
        if not key or not secret:
            raise ValueError(
                "TOKOCRYPTO_API_KEY and TOKOCRYPTO_API_SECRET must be set in environment"
            )
        return cls(api_key=key, api_secret=secret)

    def is_present(self) -> bool:
        return bool(self.api_key and self.api_secret)


def sign_params(
    secret: str,
    params: Mapping[str, str | int | float],
) -> str:
    """HMAC-SHA256 over totalParams (query string form). Signature is lowercase hex."""
    items = sorted((str(k), str(v)) for k, v in params.items() if v is not None)
    total = urlencode(items)
    digest = hmac.new(
        secret.encode("utf-8"),
        total.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest


def build_signed_params(
    secret: str,
    params: Optional[Mapping[str, str | int | float]] = None,
    *,
    recv_window: int = 5000,
    timestamp_ms: Optional[int] = None,
) -> dict[str, str]:
    """Attach timestamp, recvWindow, signature. Returns string-valued dict for query/body."""
    base: dict[str, str] = {str(k): str(v) for k, v in (params or {}).items() if v is not None}
    ts = timestamp_ms if timestamp_ms is not None else int(time.time() * 1000)
    base["timestamp"] = str(ts)
    base["recvWindow"] = str(recv_window)
    base["signature"] = sign_params(secret, base)
    return base
