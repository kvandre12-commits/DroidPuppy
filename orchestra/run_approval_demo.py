"""The approval gate: "you own every trade."

An irreversible intent (place a broker order) is submitted. The Orchestra
decomposes it, sees the task is irreversible + requires approval, and SUSPENDS -
it will not execute until the conductor explicitly approves. We show both:
the suspension, then approval -> execution. (A deny path is included too.)

Run:  python3 run_approval_demo.py    (from the orchestra/ directory)
"""

from __future__ import annotations

import datetime as dt
import os
import uuid

from adapters import MockBrokerAdapter, Registry
from kernel import Kernel
from orchestra_agent import OrchestraAgent


def _intent(statement: str, params: dict) -> dict:
    return {
        "contract_version": "1.0.0",
        "intent_id": "intent-" + uuid.uuid4().hex[:8],
        "domain": "trading",
        "statement": statement,
        "goal": {"type": "place_order", "params": params},
        "constraints": [],
        "authority": {"required": True, "approver": "conductor"},
        "priority": "high",
        "success_criteria": ["order placed only after approval"],
        "created_by": "sharpedge",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "accepted",
    }


def _print_breath(kernel, intent_id):
    for obs in kernel.get_observations(intent_id):
        print(f"   [{obs['type']:>18}] {obs['payload'].get('message', '')}")


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    contracts = os.path.join(here, "..", "contracts", "v1")
    db_path = os.path.join(here, ".orchestra_approval_demo.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    kernel = Kernel(db_path)
    registry = Registry()
    broker = MockBrokerAdapter()
    registry.register(broker)
    orchestra = OrchestraAgent(kernel, registry, contracts)

    # ---- Scenario A: APPROVE ----
    print("=== SCENARIO A: order that gets APPROVED ===")
    intent = _intent("BUY 1x SPY 745C @ 2.10 limit",
                     {"side": "buy", "symbol": "SPY", "strike": 745,
                      "right": "C", "qty": 1, "limit": 2.10})
    iid = orchestra.submit(intent)
    outcome = orchestra.run(iid)

    print("\n--- breath so far ---")
    _print_breath(kernel, iid)
    print("\n--- Orchestra returned ---")
    print("    status:", outcome["status"])
    pending = outcome.get("pending_approvals", [])
    for p in pending:
        print(f"    AWAITING APPROVAL: {p['type']} ({p['side_effect_class']}) "
              f"-> {p['inputs']}")
    print("    >> orders placed so far:", len(broker.orders), "(correctly ZERO)")

    print("\n--- conductor approves ---")
    final = orchestra.approve(iid, pending[0]["task_id"], approver="conductor")
    _print_breath(kernel, iid)
    print("\n    final status:", final["status"])
    print("    >> orders placed now:", len(broker.orders), "->", broker.orders)

    # ---- Scenario B: DENY ----
    print("\n\n=== SCENARIO B: order that gets DENIED ===")
    intent2 = _intent("BUY 5x TSLA 0DTE calls (YOLO)",
                      {"side": "buy", "symbol": "TSLA", "qty": 5, "right": "C"})
    iid2 = orchestra.submit(intent2)
    outcome2 = orchestra.run(iid2)
    pend2 = outcome2.get("pending_approvals", [])
    print("    suspended, awaiting approval:", bool(pend2))
    final2 = orchestra.deny(iid2, pend2[0]["task_id"], approver="conductor",
                            reason="position too large, not today")
    print("    final status:", final2["status"])
    print("    >> total orders placed:", len(broker.orders),
          "(the denied one never executed)")


if __name__ == "__main__":
    main()
