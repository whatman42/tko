"""Invariant: only symbolType=1 is eligible for execution."""
from __future__ import annotations

from src.python.exchange.models.instrument import InstrumentMeta, SymbolType
from src.python.exchange.contracts.symbol_router import ExecutionEligibility


def _make_instrument(symbol_type: int | None) -> InstrumentMeta:
    return InstrumentMeta(
        symbol="BTC_USDT",
        base_asset="BTC",
        quote_asset="USDT",
        symbol_type=symbol_type,
        status="TRADING",
        base_precision=8,
        quote_precision=8,
    )


def test_type_1_is_executable_candidate():
    inst = _make_instrument(SymbolType.MBX)
    assert inst.is_mbx is True
    assert inst.is_nextme is False
    assert inst.symbol_type == 1


def test_type_3_is_not_executable_by_model():
    inst = _make_instrument(SymbolType.NEXTME)
    assert inst.is_mbx is False
    assert inst.is_nextme is True
    assert inst.symbol_type == 3


def test_unknown_type_is_neither():
    inst = _make_instrument(None)
    assert inst.is_mbx is False
    assert inst.is_nextme is False


def test_eligibility_enum_values_locked():
    assert ExecutionEligibility.ELIGIBLE_FOR_EXECUTION.value == "ELIGIBLE_FOR_EXECUTION"
    assert ExecutionEligibility.DISCOVERED_BUT_EXECUTION_BLOCKED.value == "DISCOVERED_BUT_EXECUTION_BLOCKED"
    assert ExecutionEligibility.BLOCK.value == "BLOCK"
