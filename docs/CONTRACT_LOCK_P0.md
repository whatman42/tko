# CONTRACT LOCK — P0 Exchange Foundation

**Status:** LOCKED  
**Date:** 2026-09-23  
**Mode:** LIVE ONLY  
**create_order:** FORBIDDEN in P0  

---

## 1. Scope of P0

P0 delivers:

- Exchange foundation (REST + Public Market WS + Private User Stream listenToken)
- SymbolRouter with dual-engine awareness
- AccountState SSOT foundation (no create_order)
- Contract interfaces + invariant tests
- Explicit evidence grades

P0 does **not** deliver:

- LiveOrderExecutor
- create_order / cancel_order
- RiskGate activation for live sizing
- Signal producer
- Telegram / Gemini
- Production enablement

---

## 2. Evidence Grades (immutable until proven otherwise)

| Grade | Value | Meaning |
|-------|-------|---------|
| API_DOCUMENTATION | VERIFIED | Official Tokocrypto docs + changelog 2026-03-30 |
| CCXT_CONTRACT | VERIFIED | `privatePostOpenV1UserListenToken` present in CCXT |
| LIVE_RUNTIME_PROOF | **UNVERIFIED** | No credential live call performed yet |
| EXECUTION_ENABLEMENT | **BLOCKED** | Production create_order disabled until RUNTIME_PROOF=VERIFIED |

Documentation ≠ runtime certification.

---

## 3. Universe Classification (locked)

```
ALL_DISCOVERED  (from GET /open/v1/common/symbols)
    ├── symbolType == 1 (MBX)
    │       → ELIGIBLE_FOR_EXECUTION
    │       → REST + Public WS + listenToken Private WS
    │
    ├── symbolType == 3 (NextMe)
    │       → DISCOVERED_BUT_EXECUTION_BLOCKED
    │       → PRIVATE_WS_UNSUPPORTED (listenToken only for type=1)
    │       → cannot reach clear_for_execution()
    │
    └── unknown / missing type
            → BLOCK
```

Invariant:

```
symbolType != 1  →  PRIVATE_WS_UNSUPPORTED  →  EXECUTION_BLOCKED
```

---

## 4. Fail-Closed Rules (must never be weakened)

| Condition | Result |
|-----------|--------|
| symbolType != 1 | EXECUTION_BLOCKED |
| STALE MARKET / WS disconnect | BLOCK create_order path |
| PRIVATE STREAM LOST / token expired without renew | BLOCK |
| RECONCILIATION UNKNOWN | BLOCK |
| INVALID CREDENTIAL | BLOCK |
| LIVE_RUNTIME_PROOF = UNVERIFIED | production execution disabled |
| UNKNOWN TYPE | BLOCK |
| metadata stale / filter missing | BLOCK |

Reconnect alone does **not** reopen the execution gate.  
Required sequence after disconnect:

```
CONNECTED → STALE/UNKNOWN → BLOCK
→ REST RESYNC → WS RESUBSCRIBE → STATE RECONCILED → EXECUTION_READY
```

---

## 5. Single Order Path (future P3+)

```
Signal
  → RiskGate
  → MarketStructureGate
  → clear_for_execution()
  → ValidatedOrder
  → LiveOrderExecutor          ← P3 only
  → Tokocrypto create_order
  → Private User Stream
  → REST reconciliation
  → OrderLifecycle
  → AccountState (SSOT)
```

No alternate path from Telegram, Gemini, strategy, scheduler, GUI, or market-data handler may call create_order.

---

## 6. P0 Interfaces (contract-first)

### ExchangeClient
- `get_server_time() -> int`
- `get_symbols() -> list[InstrumentMeta]`
- `get_account_snapshot() -> AccountSnapshot`
- `get_open_orders() -> list[OpenOrder]`
- **No create_order / cancel_order**

### SymbolRouter
- Maps `symbolType` → REST base URL + Public WS base + Private WS capability
- type=1 → executable candidate
- type=3 → observable only
- unknown → BLOCK

### PublicMarketWS
- Subscribe / unsubscribe streams (`@depth`, `@kline_*`, `@trade`, `@aggTrade`, `@miniTicker`)
- Stale detection, ping/pong, 24h reconnect handling
- Fail-closed on disconnect

### PrivateUserStream
- Only `POST /open/v1/user-listen-token` + WebSocket API `userDataStream.subscribe.listenToken`
- Scope: symbolType=1 only
- Events: `outboundAccountPosition`, `executionReport`, `eventStreamTerminated`
- Token does **not** auto-renew; must re-issue before expiry

### AccountState
- SSOT built from REST snapshot + private stream events + reconciliation
- GUI / Telegram / sizing / reporting must read from AccountState only
- Never invent balances or positions

---

## 7. Credential Policy (C1)

- API Key + Secret via environment / OS secret store / CI injection only
- `.env` allowed for local development only and **must be gitignored**
- Never commit, log, put in Telegram, artifact, or exception trace

---

## 8. Next Stages (after P0 contracts + tests pass)

1. Implement REST + WS foundation against locked contracts
2. Runtime proof with real credential (separate gate)
3. P1 — full AccountState reconciliation loop
4. P2 — Market/Instrument Safety (filters, precision, stale)
5. P3 — LiveOrderExecutor (first appearance of create_order)
6. … → P7 Certification → production enablement

---

## 9. Explicit Non-Goals of P0

- No PAPER / DEMO / DRY_RUN / SHADOW / SIMULATION flags
- No stub `create_order()` that can be accidentally called
- No silent fallback from type=1 to type=3 or vice-versa
- No legacy listenKey path

**End of Contract Lock P0**
