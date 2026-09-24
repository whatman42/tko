"""P0.5 — Composite readiness. Reconnect alone never enables execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.python.exchange.contracts.account_state import AccountState, ReconciliationStatus
from src.python.exchange.contracts.private_user_stream import PrivateStreamState, PrivateUserStream
from src.python.exchange.contracts.public_market_ws import MarketConnectionState, PublicMarketWS
from src.python.exchange.contracts.symbol_router import ExecutionEligibility, RouteResult

EXECUTION_ENABLEMENT = "BLOCKED"
LIVE_RUNTIME_PROOF = "UNVERIFIED"


@dataclass(frozen=True)
class ReadinessReport:
    ready: bool
    reasons: tuple[str, ...]
    execution_enablement: str = EXECUTION_ENABLEMENT
    live_runtime_proof: str = LIVE_RUNTIME_PROOF


def evaluate_execution_readiness(
    *,
    route: RouteResult,
    public_ws: Optional[PublicMarketWS] = None,
    private_ws: Optional[PrivateUserStream] = None,
    account: Optional[AccountState] = None,
    max_public_stale_ms: int = 5_000,
) -> ReadinessReport:
    reasons: list[str] = []

    if route.eligibility != ExecutionEligibility.ELIGIBLE_FOR_EXECUTION:
        reasons.append(f"route_eligibility={route.eligibility.value}")

    if not route.private_ws_supported:
        reasons.append("private_ws_unsupported_for_symbol_type")

    if public_ws is not None:
        st = public_ws.connection_state()
        if st != MarketConnectionState.CONNECTED:
            reasons.append(f"public_ws={st.value}")
        elif not public_ws.is_ready_for_execution(max_stale_ms=max_public_stale_ms):
            reasons.append("public_ws_stale_or_no_data")

    if private_ws is not None:
        pst = private_ws.stream_state()
        if pst != PrivateStreamState.SUBSCRIBED:
            reasons.append(f"private_ws={pst.value}")
        if route.symbol_type is not None and not private_ws.is_supported_for_symbol_type(
            route.symbol_type
        ):
            reasons.append("private_ws_type_gate")

    if account is not None:
        if account.reconciliation_status != ReconciliationStatus.RECONCILED:
            reasons.append(f"account_recon={account.reconciliation_status.value}")
        if not account.is_ready_for_execution():
            reasons.append("account_not_ready")

    if EXECUTION_ENABLEMENT != "ENABLED":
        reasons.append("EXECUTION_ENABLEMENT=BLOCKED")

    if LIVE_RUNTIME_PROOF != "VERIFIED":
        reasons.append("LIVE_RUNTIME_PROOF=UNVERIFIED")

    ready = len(reasons) == 0
    return ReadinessReport(
        ready=ready,
        reasons=tuple(reasons),
        execution_enablement=EXECUTION_ENABLEMENT,
        live_runtime_proof=LIVE_RUNTIME_PROOF,
    )
