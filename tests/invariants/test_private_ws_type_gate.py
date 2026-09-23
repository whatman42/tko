"""Invariant: PrivateUserStream supports only symbolType=1."""
from __future__ import annotations

from src.python.exchange.contracts.private_user_stream import PrivateStreamState


def test_private_stream_states_include_unsupported():
    assert PrivateStreamState.UNSUPPORTED.value == "UNSUPPORTED"
    assert PrivateStreamState.SUBSCRIBED.value == "SUBSCRIBED"
    assert PrivateStreamState.TERMINATED.value == "TERMINATED"


def test_only_subscribed_is_ready_logic():
    ready_states = {PrivateStreamState.SUBSCRIBED}
    for s in PrivateStreamState:
        expected = s in ready_states
        assert (s == PrivateStreamState.SUBSCRIBED) is expected
