"""P2 must not expose order submission."""
from __future__ import annotations

import inspect

import src.python.governance.market_structure.gate as gate_mod
from src.python.governance.market_structure.gate import MarketStructureGate

FORBIDDEN = {"create_order", "cancel_order", "place_order", "submit_order"}


def test_gate_has_no_order_methods():
    methods = {
        n
        for n, _ in inspect.getmembers(MarketStructureGate, predicate=inspect.isfunction)
        if not n.startswith("_")
    }
    assert not (methods & FORBIDDEN)
    assert "validate" in methods


def test_module_source_has_no_create_order_string_as_method():
    src = inspect.getsource(gate_mod)
    assert "def create_order" not in src
    assert "def cancel_order" not in src
