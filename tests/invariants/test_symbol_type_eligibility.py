"""Universe eligibility: type=1 only for execution path."""
from __future__ import annotations

from src.python.exchange.contracts.symbol_router import ExecutionEligibility
from src.python.exchange.models.instrument import InstrumentMeta
from src.python.exchange.tokocrypto.symbol_router import TokocryptoSymbolRouter


def test_type1_eligible_type3_blocked():
    router = TokocryptoSymbolRouter()
    mbx = InstrumentMeta(
        symbol="BTC_USDT", base_asset="BTC", quote_asset="USDT",
        symbol_type=1, status="TRADING", base_precision=8, quote_precision=8,
    )
    nextme = InstrumentMeta(
        symbol="SOL_IDR", base_asset="SOL", quote_asset="IDR",
        symbol_type=3, status="TRADING", base_precision=8, quote_precision=0,
    )
    assert router.classify(mbx).eligibility == ExecutionEligibility.ELIGIBLE_FOR_EXECUTION
    assert router.classify(nextme).eligibility == ExecutionEligibility.DISCOVERED_BUT_EXECUTION_BLOCKED
