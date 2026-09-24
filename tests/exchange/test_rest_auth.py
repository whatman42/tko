"""Auth signing unit tests — deterministic HMAC."""
from __future__ import annotations

from src.python.exchange.tokocrypto.rest.auth import build_signed_params, sign_params


def test_sign_params_stable():
    secret = "testsecret"
    params = {"symbol": "BTC_USDT", "timestamp": "1581720670624", "recvWindow": "5000"}
    sig1 = sign_params(secret, params)
    sig2 = sign_params(secret, params)
    assert sig1 == sig2
    assert len(sig1) == 64


def test_build_signed_params_includes_signature():
    out = build_signed_params(
        "testsecret",
        {"symbol": "BTC_USDT"},
        recv_window=5000,
        timestamp_ms=1581720670624,
    )
    assert "signature" in out
    assert out["timestamp"] == "1581720670624"
    assert out["recvWindow"] == "5000"
    assert out["symbol"] == "BTC_USDT"
