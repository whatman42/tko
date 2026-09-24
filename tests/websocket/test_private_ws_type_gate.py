"""Private WS type gate + state — no live network."""
from __future__ import annotations

from src.python.exchange.contracts.private_user_stream import PrivateStreamState
from src.python.exchange.tokocrypto.websocket.private_ws import TokocryptoPrivateUserStream


def test_only_type1_supported():
    s = TokocryptoPrivateUserStream()
    assert s.is_supported_for_symbol_type(1) is True
    assert s.is_supported_for_symbol_type(3) is False
    assert s.is_supported_for_symbol_type(2) is False
    assert s.is_supported_for_symbol_type(0) is False


def test_not_ready_until_subscribed():
    s = TokocryptoPrivateUserStream()
    assert s.is_ready_for_execution() is False
    s.force_state(PrivateStreamState.TOKEN_REQUESTED)
    assert s.is_ready_for_execution() is False
    s.force_state(PrivateStreamState.SUBSCRIBED)
    assert s.is_ready_for_execution() is True
    s.force_state(PrivateStreamState.TERMINATED)
    assert s.is_ready_for_execution() is False
    s.force_state(PrivateStreamState.UNSUPPORTED)
    assert s.is_ready_for_execution() is False


def test_create_token_requires_creds():
    s = TokocryptoPrivateUserStream(credentials=None)
    try:
        s.create_listen_token()
        assert False
    except RuntimeError as e:
        assert "credential" in str(e).lower()
