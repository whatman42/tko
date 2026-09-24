"""MarketStructureGate — P2. Validates OrderIntent; never submits orders."""
from __future__ import annotations

from typing import Mapping, Optional

from src.python.exchange.models.instrument import InstrumentMeta
from src.python.exchange.tokocrypto.symbol_router import TokocryptoSymbolRouter
from src.python.exchange.contracts.symbol_router import ExecutionEligibility
from src.python.governance.market_structure.decimal_rules import (
    validate_notional,
    validate_precision_strings,
    validate_price,
    validate_quantity,
)
from src.python.governance.market_structure.market_state import MarketHealth, MarketState
from src.python.governance.market_structure.types import (
    BlockReason,
    GateResult,
    GateVerdict,
    OrderIntent,
)

_TRADING_STATUSES = frozenset(
    {
        "TRADING",
        "trading",
        "ENABLED",
        "enabled",
        "1",
    }
)


class MarketStructureGate:
    """Fail-closed instrument + market + filter validation. No silent rounding."""

    def __init__(
        self,
        *,
        instruments: Optional[Mapping[str, InstrumentMeta]] = None,
        router: Optional[TokocryptoSymbolRouter] = None,
        require_price_filter: bool = True,
        require_lot_filter: bool = True,
    ) -> None:
        self._instruments = {k.upper(): v for k, v in (instruments or {}).items()}
        self._router = router or TokocryptoSymbolRouter()
        self._require_price = require_price_filter
        self._require_lot = require_lot_filter

    def set_instruments(self, instruments: Mapping[str, InstrumentMeta]) -> None:
        self._instruments = {k.upper(): v for k, v in instruments.items()}

    def _lookup(self, symbol: str) -> Optional[InstrumentMeta]:
        return self._instruments.get(symbol.upper().replace("-", "_")) or self._instruments.get(
            symbol.upper()
        )

    def validate(
        self,
        intent: OrderIntent,
        *,
        market: Optional[MarketState] = None,
    ) -> GateResult:
        checks: list[str] = []
        sym = (intent.symbol or "").upper()

        if not sym or not intent.price or not intent.quantity:
            return GateResult(
                GateVerdict.BLOCK,
                BlockReason.INVALID_INTENT,
                "missing symbol/price/quantity",
                symbol=sym,
            )

        prec_fail = validate_precision_strings(intent.price, intent.quantity)
        if prec_fail:
            return GateResult(
                GateVerdict.BLOCK,
                BlockReason.PRECISION,
                "; ".join(prec_fail),
                symbol=sym,
                checks=tuple(prec_fail),
            )
        checks.append("precision_ok")

        inst = self._lookup(sym)
        if inst is None:
            return GateResult(
                GateVerdict.BLOCK,
                BlockReason.SYMBOL_NOT_FOUND,
                f"symbol {sym} not in universe",
                symbol=sym,
            )
        checks.append("symbol_found")

        route = self._router.classify(inst)
        if route.eligibility != ExecutionEligibility.ELIGIBLE_FOR_EXECUTION:
            return GateResult(
                GateVerdict.BLOCK,
                BlockReason.SYMBOL_TYPE_NOT_EXECUTABLE,
                route.reason,
                symbol=sym,
                checks=tuple(checks),
            )
        checks.append("symbol_type_ok")

        status = (inst.status or "").strip()
        if status not in _TRADING_STATUSES:
            return GateResult(
                GateVerdict.BLOCK,
                BlockReason.INSTRUMENT_NOT_TRADING,
                f"status={status!r}",
                symbol=sym,
                checks=tuple(checks),
            )
        checks.append("status_trading")

        if market is not None:
            if not market.metadata_ok():
                return GateResult(
                    GateVerdict.BLOCK,
                    BlockReason.METADATA_STALE,
                    f"metadata_age_ms={market.metadata_age_ms}",
                    symbol=sym,
                    checks=tuple(checks),
                )
            health = market.health()
            if health == MarketHealth.DISCONNECTED:
                return GateResult(
                    GateVerdict.BLOCK,
                    BlockReason.MARKET_DISCONNECTED,
                    "public market ws disconnected",
                    symbol=sym,
                    checks=tuple(checks),
                )
            if health == MarketHealth.STALE:
                return GateResult(
                    GateVerdict.STALE,
                    BlockReason.MARKET_STALE,
                    f"age_ms={market.last_message_age_ms}",
                    symbol=sym,
                    checks=tuple(checks),
                )
            if health == MarketHealth.UNKNOWN:
                return GateResult(
                    GateVerdict.UNKNOWN,
                    BlockReason.MARKET_UNKNOWN,
                    "market health unknown",
                    symbol=sym,
                    checks=tuple(checks),
                )
            checks.append("market_ok")

        if self._require_price or inst.price_filter is not None:
            pf_fail = validate_price(intent.price, inst.price_filter)
            if pf_fail:
                if any("METADATA_MISSING" in f for f in pf_fail):
                    reason = BlockReason.METADATA_MISSING
                elif any("PRICE_FILTER" in f for f in pf_fail):
                    reason = BlockReason.PRICE_FILTER
                elif any("PRICE_TICK" in f for f in pf_fail):
                    reason = BlockReason.PRICE_TICK
                else:
                    reason = BlockReason.PRICE_FILTER
                return GateResult(
                    GateVerdict.BLOCK,
                    reason,
                    "; ".join(pf_fail),
                    symbol=sym,
                    checks=tuple(checks + pf_fail),
                )
            checks.append("price_ok")

        is_market = (intent.order_type or "").upper() == "MARKET"
        if self._require_lot or inst.lot_size is not None:
            q_fail = validate_quantity(
                intent.quantity,
                inst.lot_size,
                market=is_market,
                market_lot=inst.market_lot_size,
            )
            if q_fail:
                reason = BlockReason.LOT_SIZE
                if any("QTY_BELOW_MIN" in f for f in q_fail):
                    reason = BlockReason.QTY_BELOW_MIN
                elif any("QTY_ABOVE_MAX" in f for f in q_fail):
                    reason = BlockReason.QTY_ABOVE_MAX
                elif any("METADATA_MISSING" in f for f in q_fail):
                    reason = BlockReason.METADATA_MISSING
                return GateResult(
                    GateVerdict.BLOCK,
                    reason,
                    "; ".join(q_fail),
                    symbol=sym,
                    checks=tuple(checks + q_fail),
                )
            checks.append("qty_ok")

        n_fail = validate_notional(intent.price, intent.quantity, inst.notional)
        if n_fail:
            return GateResult(
                GateVerdict.BLOCK,
                BlockReason.NOTIONAL,
                "; ".join(n_fail),
                symbol=sym,
                checks=tuple(checks + n_fail),
            )
        checks.append("notional_ok")

        return GateResult(
            GateVerdict.PASS,
            BlockReason.NONE,
            "all constraints satisfied",
            symbol=sym,
            checks=tuple(checks),
        )
