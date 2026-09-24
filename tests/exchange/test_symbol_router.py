"""SymbolRouter concrete — type=1 executable, type=3 blocked, unknown block."""
from __future__ import annotations

from src.python.exchange.contracts.symbol_router import ExecutionEligibility
from src.python.exchange.models.instrument import InstrumentMeta
from src.python.exchange.tokocrypto.symbol_router import TokocryptoSymbolRouter


def _inst(symbol: str, st: int | None) -> InstrumentMeta:
    return InstrumentMeta(
        symbol=symbol,
        base_asset="X",
        quote_asset="USDT",
        symbol_type=st,
        status="TRADING",
        base_precision=8,
        quote_precision=8,
    )


def test_type1_eligible():
    r = TokocryptoSymbolRouter().classify(_inst("BTC_USDT", 1))
    assert r.eligibility == ExecutionEligibility.ELIGIBLE_FOR_EXECUTION
    assert r.private_ws_supported is True
    assert r.public_ws_base is not None
    assert "stream-cloud" in (r.public_ws_base or "")


def test_type3_discovered_but_blocked():
    r = TokocryptoSymbolRouter().classify(_inst("SOL_IDR", 3))
    assert r.eligibility == ExecutionEligibility.DISCOVERED_BUT_EXECUTION_BLOCKED
    assert r.private_ws_supported is False
    assert "2meta" in (r.public_ws_base or "")


def test_unknown_type_block():
    r = TokocryptoSymbolRouter().classify(_inst("FOO", None))
    assert r.eligibility == ExecutionEligibility.BLOCK
    assert r.private_ws_supported is False
    assert r.rest_base is None


def test_type2_or_other_block():
    r = TokocryptoSymbolRouter().classify(_inst("Z", 2))
    assert r.eligibility == ExecutionEligibility.BLOCK


def test_route_for_symbol_found_and_missing():
    router = TokocryptoSymbolRouter()
    universe = [_inst("BTC_USDT", 1), _inst("ETH_USDT", 3)]
    ok = router.route_for_symbol("btc_usdt", universe)
    assert ok.eligibility == ExecutionEligibility.ELIGIBLE_FOR_EXECUTION
    missing = router.route_for_symbol("NOPE", universe)
    assert missing.eligibility == ExecutionEligibility.BLOCK
    assert "not found" in missing.reason


def test_is_executable_helper():
    router = TokocryptoSymbolRouter()
    assert router.is_executable(_inst("A", 1)) is True
    assert router.is_executable(_inst("B", 3)) is False
    assert router.is_executable(_inst("C", None)) is False
