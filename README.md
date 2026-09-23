# TKO — Tokocrypto LIVE ONLY

**Mode:** LIVE ONLY (no PAPER / DEMO / DRY_RUN / SHADOW / SIMULATION runtime flags)  
**Phase:** P0 — Exchange Foundation (contract-first)  
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

## Structure

```
src/python/
  exchange/
    contracts/     ← P0 interfaces (ExchangeClient, SymbolRouter, PublicMarketWS,
                     PrivateUserStream, AccountState)
    models/
    tokocrypto/    ← concrete implementations (to be filled)
  governance/      ← risk / execution / readiness / market_structure (from IDX patterns)
  runtime/
docs/
  CONTRACT_LOCK_P0.md
tests/
  contracts/
  invariants/
```

## Quick check

```bash
pip install -e .
pytest -q
```

## Next

1. Implement concrete REST + WS against locked contracts  
2. Runtime proof with real credentials (separate gate)  
3. P1 AccountState reconciliation loop  
4. … → P3 LiveOrderExecutor (first appearance of create_order)

See `docs/CONTRACT_LOCK_P0.md` for full locked rules.
