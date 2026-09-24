"""Contract tests for REST parsers — no network."""
from __future__ import annotations

from src.python.exchange.tokocrypto.rest.parsers import (
    parse_account_snapshot,
    parse_instrument,
    parse_open_orders,
    parse_server_time,
    parse_symbols_response,
)


def test_parse_server_time_nested():
    assert parse_server_time({"code": 0, "data": {"serverTime": 1700000000123}}) == 1700000000123


def test_parse_server_time_flat():
    assert parse_server_time({"serverTime": 99}) == 99


def test_parse_instrument_type1_with_filters():
    raw = {
        "symbol": "BTC_USDT",
        "baseAsset": "BTC",
        "quoteAsset": "USDT",
        "type": 1,
        "status": "TRADING",
        "basePrecision": 8,
        "quotePrecision": 8,
        "filters": [
            {"filterType": "PRICE_FILTER", "minPrice": "0.01", "maxPrice": "1e8", "tickSize": "0.01"},
            {"filterType": "LOT_SIZE", "minQty": "0.0001", "maxQty": "9000", "stepSize": "0.0001"},
            {"filterType": "NOTIONAL", "minNotional": "10"},
        ],
    }
    inst = parse_instrument(raw)
    assert inst.symbol == "BTC_USDT"
    assert inst.symbol_type == 1
    assert inst.is_mbx
    assert inst.price_filter is not None
    assert inst.price_filter.tick_size == "0.01"
    assert inst.lot_size is not None
    assert inst.notional is not None
    assert inst.notional.min_notional == "10"


def test_parse_instrument_type3():
    inst = parse_instrument({"symbol": "SOL_IDR", "type": 3, "baseAsset": "SOL", "quoteAsset": "IDR"})
    assert inst.symbol_type == 3
    assert inst.is_nextme


def test_parse_symbols_list_shape():
    payload = {
        "code": 0,
        "data": [
            {"symbol": "A_USDT", "type": 1, "baseAsset": "A", "quoteAsset": "USDT"},
            {"symbol": "B_IDR", "type": 3, "baseAsset": "B", "quoteAsset": "IDR"},
        ],
    }
    out = parse_symbols_response(payload)
    assert len(out) == 2
    assert out[0].symbol_type == 1
    assert out[1].symbol_type == 3


def test_parse_account_snapshot():
    payload = {
        "code": 0,
        "data": {
            "canTrade": True,
            "balances": [
                {"asset": "USDT", "free": "100.5", "locked": "1.0"},
                {"asset": "BTC", "free": "0.01", "locked": "0"},
            ],
        },
    }
    snap = parse_account_snapshot(payload)
    assert snap.can_trade is True
    assert len(snap.balances) == 2
    assert snap.balances[0].asset == "USDT"
    assert snap.balances[0].free == "100.5"


def test_parse_open_orders():
    payload = {
        "code": 0,
        "data": [
            {
                "symbol": "BTC_USDT",
                "orderId": "123",
                "clientId": "c1",
                "side": 0,
                "type": 1,
                "price": "50000",
                "origQty": "0.01",
                "executedQty": "0",
                "status": "NEW",
                "symbolType": 1,
            }
        ],
    }
    orders = parse_open_orders(payload)
    assert len(orders) == 1
    assert orders[0].order_id == "123"
    assert orders[0].symbol_type == 1
