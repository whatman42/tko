"""Invariant: concrete REST client still has no create_order."""
from __future__ import annotations

import inspect

from src.python.exchange.tokocrypto.rest.client import TokocryptoRestClient

FORBIDDEN = {
    "create_order",
    "cancel_order",
    "place_order",
    "submit_order",
    "new_order",
}


def test_concrete_client_has_no_order_methods():
    methods = {
        name
        for name, _ in inspect.getmembers(TokocryptoRestClient, predicate=inspect.isfunction)
        if not name.startswith("_")
    }
    assert not (methods & FORBIDDEN)
