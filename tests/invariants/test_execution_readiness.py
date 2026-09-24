"""P0.5 composite readiness — EXECUTION_ENABLEMENT always BLOCKED in P0."""
from __future__ import annotations

from src.python.exchange.contracts.account_state import AccountState, ReconciliationStatus
from src.python.exchange.contracts.private_user_stream import PrivateStreamState
from src.python.exchange.contracts.public_market_ws import MarketConnectionState
from src.python.exchange.contracts.symbol_router import ExecutionEligibility, RouteResult
from src.python.exchange.models.account import AccountSnapshot, Balance
from src.python.exchange.tokocrypto.execution_readiness import (
    EXECUTION_ENABLEMENT,
    LIVE_RUNTIME_PROOF,
    evaluate_execution_readiness,
)
from src.python.exchange.tokocrypto.websocket.private_ws import TokocryptoPrivateUserStream
from src.python.exchange.tokocrypto.websocket.public_ws import TokocryptoPublicMarketWS


def _eligible_route() -> RouteResult:
    return RouteResult(
        symbol="BTC_USDT",
        symbol_type=1,
        eligibility=ExecutionEligibility.ELIGIBLE_FOR_EXECUTION,
        rest_base="https://www.tokocrypto.com",
        public_ws_base="wss://stream-cloud.tokocrypto.site/stream",
        private_ws_supported=True,
        reason="ok",
    )


def test_execution_enablement_constant_blocked():
    assert EXECUTION_ENABLEMENT == "BLOCKED"
    assert LIVE_RUNTIME_PROOF == "UNVERIFIED"


def test_even_perfect_local_state_not_ready_in_p0():
    pub = TokocryptoPublicMarketWS()
    pub.force_state(MarketConnectionState.CONNECTED)
    pub.mark_message_received()
    priv = TokocryptoPrivateUserStream()
    priv.force_state(PrivateStreamState.SUBSCRIBED)
    acct = AccountState(
        snapshot=AccountSnapshot(balances=(Balance("USDT", "1", "0"),)),
        reconciliation_status=ReconciliationStatus.RECONCILED,
    )
    report = evaluate_execution_readiness(
        route=_eligible_route(),
        public_ws=pub,
        private_ws=priv,
        account=acct,
    )
    assert report.ready is False
    assert "EXECUTION_ENABLEMENT=BLOCKED" in report.reasons
    assert "LIVE_RUNTIME_PROOF=UNVERIFIED" in report.reasons


def test_type3_route_blocked():
    route = RouteResult(
        symbol="X",
        symbol_type=3,
        eligibility=ExecutionEligibility.DISCOVERED_BUT_EXECUTION_BLOCKED,
        rest_base=None,
        public_ws_base=None,
        private_ws_supported=False,
        reason="type3",
    )
    report = evaluate_execution_readiness(route=route)
    assert report.ready is False
    assert any("route_eligibility" in r or "private_ws" in r for r in report.reasons)


def test_stale_public_blocks():
    pub = TokocryptoPublicMarketWS()
    pub.force_state(MarketConnectionState.STALE)
    report = evaluate_execution_readiness(route=_eligible_route(), public_ws=pub)
    assert report.ready is False
    assert any("public_ws" in r for r in report.reasons)
