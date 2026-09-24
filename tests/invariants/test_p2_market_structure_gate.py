"""P2 MarketStructureGate — all fail-closed paths."""
from __future__ import annotations

from src.python.exchange.contracts.public_market_ws import MarketConnectionState
from src.python.exchange.models.instrument import (
    InstrumentMeta,
    LotSizeFilter,
    NotionalFilter,
    PriceFilter,
)
from src.python.governance.market_structure import (
    BlockReason,
    GateVerdict,
    MarketState,
    MarketStructureGate,
    OrderIntent,
)


def _inst(
    symbol: str = "BTC_USDT",
    *,
    st: int = 1,
    status: str = "TRADING",
    tick: str = "0.01",
    step: str = "0.0001",
    min_qty: str = "0.0001",
    min_notional: str | None = "10",
) -> InstrumentMeta:
    return InstrumentMeta(
        symbol=symbol,
        base_asset="BTC",
        quote_asset="USDT",
        symbol_type=st,
        status=status,
        base_precision=8,
        quote_precision=8,
        price_filter=PriceFilter(min_price="0.01", max_price="1000000", tick_size=tick),
        lot_size=LotSizeFilter(min_qty=min_qty, max_qty="9000", step_size=step),
        notional=NotionalFilter(min_notional=min_notional) if min_notional else None,
    )


def _gate(*instruments: InstrumentMeta) -> MarketStructureGate:
    return MarketStructureGate(instruments={i.symbol: i for i in instruments})


def _ok_market() -> MarketState:
    return MarketState(
        connection=MarketConnectionState.CONNECTED,
        last_message_age_ms=100,
        max_stale_ms=5_000,
    )


def test_pass_happy_path():
    g = _gate(_inst())
    r = g.validate(
        OrderIntent("BTC_USDT", "BUY", "50000.00", "0.001"),
        market=_ok_market(),
    )
    assert r.verdict == GateVerdict.PASS
    assert r.allow is True
    assert r.reason == BlockReason.NONE


def test_symbol_not_found():
    g = _gate(_inst())
    r = g.validate(OrderIntent("NOPE", "BUY", "1", "1"), market=_ok_market())
    assert r.verdict == GateVerdict.BLOCK
    assert r.reason == BlockReason.SYMBOL_NOT_FOUND


def test_type3_blocked():
    g = _gate(_inst("ADA_IDR", st=3))
    r = g.validate(OrderIntent("ADA_IDR", "BUY", "10000", "1"), market=_ok_market())
    assert r.verdict == GateVerdict.BLOCK
    assert r.reason == BlockReason.SYMBOL_TYPE_NOT_EXECUTABLE


def test_status_halted():
    g = _gate(_inst(status="BREAK"))
    r = g.validate(OrderIntent("BTC_USDT", "BUY", "50000.00", "0.001"), market=_ok_market())
    assert r.reason == BlockReason.INSTRUMENT_NOT_TRADING


def test_market_disconnected():
    g = _gate(_inst())
    m = MarketState(connection=MarketConnectionState.DISCONNECTED)
    r = g.validate(OrderIntent("BTC_USDT", "BUY", "50000.00", "0.001"), market=m)
    assert r.reason == BlockReason.MARKET_DISCONNECTED


def test_market_stale():
    g = _gate(_inst())
    m = MarketState(
        connection=MarketConnectionState.CONNECTED,
        last_message_age_ms=60_000,
        max_stale_ms=5_000,
    )
    r = g.validate(OrderIntent("BTC_USDT", "BUY", "50000.00", "0.001"), market=m)
    assert r.verdict == GateVerdict.STALE
    assert r.reason == BlockReason.MARKET_STALE


def test_market_unknown_no_messages():
    g = _gate(_inst())
    m = MarketState(connection=MarketConnectionState.CONNECTED, last_message_age_ms=None)
    r = g.validate(OrderIntent("BTC_USDT", "BUY", "50000.00", "0.001"), market=m)
    assert r.verdict == GateVerdict.UNKNOWN


def test_price_not_on_tick():
    g = _gate(_inst(tick="0.01"))
    r = g.validate(
        OrderIntent("BTC_USDT", "BUY", "50000.005", "0.001"),
        market=_ok_market(),
    )
    assert r.verdict == GateVerdict.BLOCK
    assert r.reason == BlockReason.PRICE_TICK


def test_price_below_min():
    g = _gate(_inst())
    r = g.validate(
        OrderIntent("BTC_USDT", "BUY", "0.001", "0.001"),
        market=_ok_market(),
    )
    assert r.reason == BlockReason.PRICE_FILTER


def test_qty_not_on_step():
    g = _gate(_inst(step="0.001"))
    r = g.validate(
        OrderIntent("BTC_USDT", "BUY", "50000.00", "0.0015"),
        market=_ok_market(),
    )
    assert r.reason == BlockReason.LOT_SIZE


def test_qty_below_min():
    g = _gate(_inst(min_qty="0.01", step="0.01"))
    r = g.validate(
        OrderIntent("BTC_USDT", "BUY", "50000.00", "0.001"),
        market=_ok_market(),
    )
    assert r.reason == BlockReason.QTY_BELOW_MIN


def test_notional_too_small():
    g = _gate(_inst(min_notional="100"))
    r = g.validate(
        OrderIntent("BTC_USDT", "BUY", "50.00", "0.001"),
        market=_ok_market(),
    )
    assert r.reason == BlockReason.NOTIONAL


def test_invalid_precision_scientific():
    g = _gate(_inst())
    r = g.validate(
        OrderIntent("BTC_USDT", "BUY", "5e4", "0.001"),
        market=_ok_market(),
    )
    assert r.reason == BlockReason.PRECISION


def test_metadata_missing_price_filter():
    inst = InstrumentMeta(
        symbol="X_USDT",
        base_asset="X",
        quote_asset="USDT",
        symbol_type=1,
        status="TRADING",
        base_precision=8,
        quote_precision=8,
        price_filter=None,
        lot_size=LotSizeFilter("0.1", "100", "0.1"),
    )
    g = MarketStructureGate(instruments={"X_USDT": inst}, require_price_filter=True)
    r = g.validate(OrderIntent("X_USDT", "BUY", "1.0", "1.0"), market=_ok_market())
    assert r.reason == BlockReason.METADATA_MISSING


def test_no_partial_pass_on_first_failure():
    g = _gate(_inst("Z_USDT", st=3))
    r = g.validate(OrderIntent("Z_USDT", "BUY", "1.00", "1"), market=_ok_market())
    assert r.allow is False
    assert r.verdict != GateVerdict.PASS
