"""REST client with httpx mock transport — no live network."""
from __future__ import annotations

import httpx

from src.python.exchange.tokocrypto.rest.auth import Credentials
from src.python.exchange.tokocrypto.rest.client import TokocryptoRestClient


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/open/v1/common/time"):
        return httpx.Response(200, json={"code": 0, "data": {"serverTime": 111}})
    if path.endswith("/open/v1/common/symbols"):
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": [
                    {
                        "symbol": "BTC_USDT",
                        "baseAsset": "BTC",
                        "quoteAsset": "USDT",
                        "type": 1,
                        "status": "TRADING",
                        "basePrecision": 8,
                        "quotePrecision": 8,
                        "filters": [],
                    },
                    {
                        "symbol": "ADA_IDR",
                        "baseAsset": "ADA",
                        "quoteAsset": "IDR",
                        "type": 3,
                        "status": "TRADING",
                        "basePrecision": 8,
                        "quotePrecision": 0,
                        "filters": [],
                    },
                ],
            },
        )
    if path.endswith("/open/v1/account/spot"):
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "canTrade": True,
                    "balances": [{"asset": "USDT", "free": "50", "locked": "0"}],
                },
            },
        )
    if path.endswith("/open/v1/orders"):
        return httpx.Response(200, json={"code": 0, "data": []})
    return httpx.Response(404, json={"code": -1, "msg": "not found"})


def test_get_server_time_and_symbols_public():
    transport = httpx.MockTransport(_handler)
    with TokocryptoRestClient(transport=transport) as client:
        assert client.get_server_time() == 111
        symbols = client.get_symbols()
        assert len(symbols) == 2
        assert symbols[0].symbol_type == 1
        assert symbols[1].symbol_type == 3


def test_signed_endpoints_with_creds():
    transport = httpx.MockTransport(_handler)
    creds = Credentials(api_key="k", api_secret="s")
    with TokocryptoRestClient(transport=transport, credentials=creds) as client:
        snap = client.get_account_snapshot()
        assert snap.balances[0].asset == "USDT"
        assert client.get_open_orders() == []


def test_signed_without_creds_raises():
    transport = httpx.MockTransport(_handler)
    with TokocryptoRestClient(transport=transport) as client:
        try:
            client.get_account_snapshot()
            assert False, "expected RuntimeError"
        except RuntimeError as e:
            assert "TOKOCRYPTO_API" in str(e)
