#!/usr/bin/env python3
"""P0.7 Live runtime contract proof against Tokocrypto.

Guards (LOCKED):
  - Never calls create_order / cancel_order
  - Never prints secrets, tokens, signatures, or balance amounts
  - Live failure → exit non-zero (no mock fallback)
  - EXECUTION_ENABLEMENT remains BLOCKED in artifact
  - LIVE_RUNTIME_PROOF becomes VERIFIED only if all required steps pass

Usage (CI):
  python scripts/p0_runtime_proof.py --out artifacts/p0-runtime-proof.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _bool_env_ready() -> bool:
    return bool(
        os.environ.get("TOKOCRYPTO_API_KEY", "").strip()
        and os.environ.get("TOKOCRYPTO_API_SECRET", "").strip()
    )


def _base_report() -> dict[str, Any]:
    return {
        "api_documentation": "VERIFIED",
        "ccxt_contract": "VERIFIED",
        "live_runtime_proof": "FAILED",
        "execution_enablement": "BLOCKED",
        "create_order_called": False,
        "cancel_order_called": False,
        "symbol_type_1_verified": False,
        "listen_token_verified": False,
        "account_snapshot_verified": False,
        "open_orders_verified": False,
        "private_ws_verified": False,
        "reconciliation_verified": False,
        "server_time_verified": False,
        "symbols_verified": False,
        "steps": [],
        "errors": [],
    }


def _step(report: dict[str, Any], name: str, ok: bool, detail: str = "") -> None:
    entry: dict[str, Any] = {"name": name, "ok": ok}
    if detail:
        entry["detail"] = detail[:200]
    report["steps"].append(entry)
    if not ok and detail:
        report["errors"].append(f"{name}: {detail[:200]}")


def run_proof(*, private_ws_timeout_s: float = 15.0) -> dict[str, Any]:
    report = _base_report()
    if not _bool_env_ready():
        report["errors"].append(
            "missing TOKOCRYPTO_API_KEY or TOKOCRYPTO_API_SECRET in environment"
        )
        return report

    from src.python.exchange.tokocrypto.rest.auth import Credentials
    from src.python.exchange.tokocrypto.rest.client import TokocryptoRestClient
    from src.python.exchange.tokocrypto.websocket.private_ws import TokocryptoPrivateUserStream
    from src.python.runtime.state.store import InMemoryAccountStateStore
    from src.python.runtime.state.reconciler import AccountReconciler

    creds = Credentials.from_env()
    client = TokocryptoRestClient(credentials=creds)
    try:
        try:
            ts = client.get_server_time()
            ok = isinstance(ts, int) and ts > 0
            report["server_time_verified"] = ok
            _step(report, "get_server_time", ok, "ms_ok" if ok else "invalid_time")
            if not ok:
                return report
        except Exception as e:
            _step(report, "get_server_time", False, type(e).__name__)
            return report

        try:
            symbols = client.get_symbols()
            n = len(symbols)
            type1 = [s for s in symbols if s.symbol_type == 1]
            type3 = [s for s in symbols if s.symbol_type == 3]
            ok = n > 0 and len(type1) > 0
            report["symbols_verified"] = n > 0
            report["symbol_type_1_verified"] = len(type1) > 0
            _step(report, "get_symbols", ok, f"total={n} type1={len(type1)} type3={len(type3)}")
            if not ok:
                return report
        except Exception as e:
            _step(report, "get_symbols", False, type(e).__name__)
            return report

        try:
            snap = client.get_account_snapshot()
            ok = snap is not None and snap.balances is not None
            report["account_snapshot_verified"] = ok
            _step(
                report,
                "get_account_snapshot",
                ok,
                f"n_assets={len(snap.balances)} can_trade={snap.can_trade}",
            )
            if not ok:
                return report
        except Exception as e:
            _step(report, "get_account_snapshot", False, type(e).__name__)
            return report

        try:
            orders = client.get_open_orders()
            ok = isinstance(orders, list)
            report["open_orders_verified"] = ok
            _step(report, "get_open_orders", ok, f"n_open={len(orders)}")
            if not ok:
                return report
        except Exception as e:
            _step(report, "get_open_orders", False, type(e).__name__)
            return report

        stream = TokocryptoPrivateUserStream(credentials=creds)
        if not stream.is_supported_for_symbol_type(1):
            _step(report, "listen_token_type_gate", False, "type1_not_supported")
            return report
        if stream.is_supported_for_symbol_type(3):
            _step(report, "listen_token_type3_must_be_false", False, "type3_incorrectly_supported")
            return report

        try:
            token = stream.create_listen_token()
            ok = bool(token.token) and token.expiration_time_ms > 0
            report["listen_token_verified"] = ok
            _step(
                report,
                "create_listen_token",
                ok,
                f"token_len={len(token.token)} exp_set={token.expiration_time_ms > 0}",
            )
            if not ok:
                return report
        except Exception as e:
            _step(report, "create_listen_token", False, type(e).__name__)
            return report

        private_ws_ok = False
        try:
            events: list[dict[str, Any]] = []

            def _on_event(msg: dict[str, Any]) -> None:
                events.append({"keys": sorted(msg.keys())[:12]})

            stream_ws = TokocryptoPrivateUserStream(credentials=creds, on_event=_on_event)
            token2 = stream_ws.create_listen_token()
            stream_ws.subscribe(token2)
            deadline = time.time() + private_ws_timeout_s
            while time.time() < deadline:
                st = stream_ws.stream_state().value
                if st == "SUBSCRIBED":
                    private_ws_ok = True
                    break
                if st in ("TERMINATED", "DISCONNECTED", "UNSUPPORTED"):
                    break
                time.sleep(0.25)
            if private_ws_ok:
                time.sleep(min(3.0, private_ws_timeout_s))
            st_final = stream_ws.stream_state().value
            stream_ws.unsubscribe()
            private_ws_ok = private_ws_ok and st_final in (
                "SUBSCRIBED",
                "DISCONNECTED",
                "TERMINATED",
            )
            report["private_ws_verified"] = private_ws_ok
            _step(
                report,
                "private_ws_subscribe",
                private_ws_ok,
                f"state={st_final} n_events={len(events)}",
            )
            if not private_ws_ok:
                return report
        except Exception as e:
            _step(report, "private_ws_subscribe", False, type(e).__name__)
            return report

        try:
            store = InMemoryAccountStateStore()
            rec = AccountReconciler(store, client)
            rec.full_resync()
            st = store.get()
            ok = st.is_ready_for_execution() and store.balances_for_risk() is not None
            rec.on_ws_disconnect()
            after = store.get()
            disconnect_blocks = not after.is_ready_for_execution()
            ok = ok and disconnect_blocks
            report["reconciliation_verified"] = ok
            _step(
                report,
                "rest_reconciliation",
                ok,
                f"lifecycle_after_disconnect_blocks={disconnect_blocks}",
            )
            if not ok:
                return report
        except Exception as e:
            _step(report, "rest_reconciliation", False, type(e).__name__)
            return report

        required = [
            report["server_time_verified"],
            report["symbols_verified"],
            report["symbol_type_1_verified"],
            report["account_snapshot_verified"],
            report["open_orders_verified"],
            report["listen_token_verified"],
            report["private_ws_verified"],
            report["reconciliation_verified"],
            report["create_order_called"] is False,
            report["cancel_order_called"] is False,
            report["execution_enablement"] == "BLOCKED",
        ]
        report["live_runtime_proof"] = "VERIFIED" if all(required) else "FAILED"
        return report
    finally:
        try:
            client.close()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="P0.7 Tokocrypto live runtime proof")
    parser.add_argument("--out", default="artifacts/p0-runtime-proof.json")
    parser.add_argument(
        "--private-ws-timeout",
        type=float,
        default=float(os.environ.get("P0_PROOF_WS_TIMEOUT", "15")),
    )
    args = parser.parse_args()
    report = run_proof(private_ws_timeout_s=args.private_ws_timeout)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "live_runtime_proof": report["live_runtime_proof"],
                "execution_enablement": report["execution_enablement"],
                "create_order_called": report["create_order_called"],
                "cancel_order_called": report["cancel_order_called"],
                "steps_ok": sum(1 for s in report["steps"] if s.get("ok")),
                "steps_total": len(report["steps"]),
                "artifact": str(out),
            }
        )
    )
    return 0 if report["live_runtime_proof"] == "VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
