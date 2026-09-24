"""Public WS state machine — fail-closed without live network."""
from __future__ import annotations

from src.python.exchange.contracts.public_market_ws import MarketConnectionState
from src.python.exchange.tokocrypto.websocket.public_ws import (
    TokocryptoPublicMarketWS,
    stream_name_for_mbx,
)


def test_stream_name_mbx():
    assert stream_name_for_mbx("BTC_USDT", "depth") == "btcusdt@depth"
    assert stream_name_for_mbx("ETH-USDT", "kline", "1m") == "ethusdt@kline_1m"


def test_initial_state_disconnected():
    ws = TokocryptoPublicMarketWS()
    assert ws.connection_state() == MarketConnectionState.DISCONNECTED
    assert ws.is_ready_for_execution() is False


def test_stale_after_connected_without_messages():
    ws = TokocryptoPublicMarketWS(stale_after_ms=1)
    ws.force_state(MarketConnectionState.CONNECTED)
    assert ws.is_ready_for_execution(max_stale_ms=1) is False


def test_ready_when_connected_and_fresh():
    ws = TokocryptoPublicMarketWS(stale_after_ms=60_000)
    ws.force_state(MarketConnectionState.CONNECTED)
    ws.mark_message_received()
    assert ws.connection_state() == MarketConnectionState.CONNECTED
    assert ws.is_ready_for_execution(max_stale_ms=60_000) is True


def test_disconnect_clears_readiness():
    ws = TokocryptoPublicMarketWS()
    ws.force_state(MarketConnectionState.CONNECTED)
    ws.mark_message_received()
    ws.force_state(MarketConnectionState.DISCONNECTED)
    assert ws.is_ready_for_execution() is False
