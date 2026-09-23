"""Concrete SymbolRouter — A1 dual-engine, fail-closed. P0.2."""
from __future__ import annotations

from src.python.exchange.contracts.symbol_router import (
    ExecutionEligibility,
    RouteResult,
    SymbolRouter,
)
from src.python.exchange.models.instrument import InstrumentMeta, SymbolType

MBX_REST_BASE = "https://www.tokocrypto.com"
MBX_PUBLIC_WS = "wss://stream-cloud.tokocrypto.site/stream"
NEXTME_REST_MARKET = "https://cloudme-toko.2meta.app"
NEXTME_PUBLIC_WS = "wss://stream-toko.2meta.app"


class TokocryptoSymbolRouter(SymbolRouter):
    """Classify instruments. type=1 executable; type=3 discovery-only; else BLOCK."""

    def classify(self, instrument: InstrumentMeta) -> RouteResult:
        st = instrument.symbol_type
        sym = instrument.symbol or ""

        if st == SymbolType.MBX or st == 1:
            return RouteResult(
                symbol=sym,
                symbol_type=1,
                eligibility=ExecutionEligibility.ELIGIBLE_FOR_EXECUTION,
                rest_base=MBX_REST_BASE,
                public_ws_base=MBX_PUBLIC_WS,
                private_ws_supported=True,
                reason="symbolType=1 MBX — listenToken private WS supported",
            )

        if st == SymbolType.NEXTME or st == 3:
            return RouteResult(
                symbol=sym,
                symbol_type=3,
                eligibility=ExecutionEligibility.DISCOVERED_BUT_EXECUTION_BLOCKED,
                rest_base=NEXTME_REST_MARKET,
                public_ws_base=NEXTME_PUBLIC_WS,
                private_ws_supported=False,
                reason="symbolType=3 NextMe — PRIVATE_WS_UNSUPPORTED (listenToken only for type=1)",
            )

        return RouteResult(
            symbol=sym,
            symbol_type=st,
            eligibility=ExecutionEligibility.BLOCK,
            rest_base=None,
            public_ws_base=None,
            private_ws_supported=False,
            reason=f"unknown or missing symbolType={st!r}",
        )

    def route_for_symbol(self, symbol: str, instruments: list[InstrumentMeta]) -> RouteResult:
        target = symbol.upper().replace("-", "_")
        for inst in instruments:
            if (inst.symbol or "").upper().replace("-", "_") == target:
                return self.classify(inst)
        return RouteResult(
            symbol=symbol,
            symbol_type=None,
            eligibility=ExecutionEligibility.BLOCK,
            rest_base=None,
            public_ws_base=None,
            private_ws_supported=False,
            reason="symbol not found in discovered universe",
        )
