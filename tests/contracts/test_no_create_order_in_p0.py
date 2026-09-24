"""Invariant: P0 contracts must not expose create_order / cancel_order."""
from __future__ import annotations

import inspect

from src.python.exchange.contracts.exchange_client import AbstractExchangeClient, ExchangeClient
from src.python.exchange.contracts.symbol_router import SymbolRouter
from src.python.exchange.contracts.public_market_ws import PublicMarketWS
from src.python.exchange.contracts.private_user_stream import PrivateUserStream
from src.python.exchange.contracts.account_state import AccountStateStore

FORBIDDEN_METHOD_NAMES = {
    "create_order",
    "cancel_order",
    "place_order",
    "submit_order",
    "new_order",
    "order",
}


def _public_methods(cls) -> set[str]:
    return {
        name
        for name, _ in inspect.getmembers(cls, predicate=inspect.isfunction)
        if not name.startswith("_")
    }


def test_exchange_client_has_no_order_methods():
    methods = _public_methods(AbstractExchangeClient)
    assert not (methods & FORBIDDEN_METHOD_NAMES)


def test_protocol_exchange_client_annotations_exclude_orders():
    members = getattr(ExchangeClient, "__protocol_attrs__", None) or dir(ExchangeClient)
    for name in FORBIDDEN_METHOD_NAMES:
        assert name not in members


def test_other_p0_contracts_have_no_order_methods():
    for cls in (SymbolRouter, PublicMarketWS, PrivateUserStream, AccountStateStore):
        methods = _public_methods(cls)
        assert not (methods & FORBIDDEN_METHOD_NAMES), cls.__name__
