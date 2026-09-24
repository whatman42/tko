"""Invariant: private WS only for symbolType=1."""
from __future__ import annotations

from src.python.exchange.tokocrypto.websocket.private_ws import TokocryptoPrivateUserStream


def test_type1_only():
    s = TokocryptoPrivateUserStream()
    assert s.is_supported_for_symbol_type(1) is True
    assert s.is_supported_for_symbol_type(3) is False
