# TKO — Tokocrypto LIVE ONLY

**Mode:** LIVE ONLY (no PAPER / DEMO / DRY_RUN / SHADOW / SIMULATION runtime flags)  
**Phase:** P0 Exchange Foundation + P1 AccountState SSOT  
**create_order:** FORBIDDEN until P3  

## Evidence Grades

| Grade | Status |
|-------|--------|
| API_DOCUMENTATION | VERIFIED |
| CCXT_CONTRACT | VERIFIED |
| LIVE_RUNTIME_PROOF | **UNVERIFIED** |
| EXECUTION_ENABLEMENT | **BLOCKED** |

## Universe Rule (P0)

```
symbolType == 1 (MBX)  → ELIGIBLE_FOR_EXECUTION
symbolType == 3 (NextMe) → DISCOVERED_BUT_EXECUTION_BLOCKED
unknown               → BLOCK
```

Private User Stream uses **listenToken only** (no legacy listenKey).  
listenToken is documented for symbolType=1 only.

## Implemented (P0.1–P0.5)

- REST: `TokocryptoRestClient` (time, symbols, account_snapshot, open_orders) — HMAC, env credentials
- SymbolRouter: type=1 executable / type=3 blocked / unknown block
- Public WS + Private WS (listenToken) with fail-closed state machines
- `evaluate_execution_readiness` — EXECUTION_ENABLEMENT stays **BLOCKED** in P0

## P1 AccountState (SSOT)

- `InMemoryAccountStateStore` + `AccountReconciler`
- Lifecycle: UNINITIALIZED → SNAPSHOT_LOADING → RECONCILED → LIVE_STREAMING → STALE/UNKNOWN
- Event normalize + dedup; REST snapshot authoritative
- `balances_for_risk()` returns **None** when UNKNOWN/STALE (never invent zero)
- EXECUTION_ENABLEMENT remains **BLOCKED**
- **62** tests offline

## Next

1. P0.7 runtime proof with env credentials (does not enable execution)
2. P2 Market/Instrument Safety
3. P3 LiveOrderExecutor (first create_order)

See `docs/CONTRACT_LOCK_P0.md` for full locked rules.
