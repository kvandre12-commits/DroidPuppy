"""Generalized planner + multi-step DAG, all from one intent.

A single "prepare_and_trade" goal decomposes (via a registered planner, not
hardcoded core logic) into a 3-step pipeline across THREE adapters with
dependencies, ending on an approval-gated irreversible order:

    add_to_watchlist (watchlist)
        -> open cockpit (droidpuppy, depends on step 1)
            -> place_order (broker, irreversible, awaits approval)

Run:  python3 run_pipeline_demo.py    (from the orchestra/ directory)
"""

from __future__ import annotations

import datetime as dt
import os
import uuid

from adapters import DroidPuppyAdapter, MockBrokerAdapter, Registry, WatchlistAdapter
from kernel import Kernel
from orchestra_agent import OrchestraAgent


def _breath(kernel, intent_id):
    for obs in kernel.get_observations(intent_id):
        print(f"   [{obs['type']:>18}] {obs['payload'].get('message', '')}")


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    contracts = os.path.join(here, "..", "contracts", "v1")
    db_path = os.path.join(here, ".orchestra_pipeline_demo.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    kernel = Kernel(db_path)
    registry = Registry()
    registry.register(WatchlistAdapter(kernel.db))
    registry.register(DroidPuppyAdapter())
    broker = MockBrokerAdapter()
    registry.register(broker)
    orchestra = OrchestraAgent(kernel, registry, contracts)

    print("known goal types (from planner registry):", orchestra.planners.known())

    intent = {
        "contract_version": "1.0.0",
        "intent_id": "intent-" + uuid.uuid4().hex[:8],
        "domain": "trading",
        "statement": "prepare SPY 745C: watchlist it, open the cockpit, then trade it",
        "goal": {
            "type": "prepare_and_trade",
            "params": {
                "contract": {"symbol": "SPY", "exp": "2026-06-15", "strike": 745, "right": "C"},
                "cockpit_url": "https://example.com",
                "order": {"side": "buy", "symbol": "SPY", "strike": 745,
                          "right": "C", "qty": 1, "limit": 2.10},
            },
        },
        "constraints": [],
        "authority": {"required": True, "approver": "conductor"},
        "priority": "high",
        "success_criteria": ["watchlisted", "cockpit opened", "order placed after approval"],
        "created_by": "sharpedge",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "accepted",
    }

    print("\n=== L1  WHAT ===")
    print("   ", intent["statement"])

    intent_id = orchestra.submit(intent)
    outcome = orchestra.run(intent_id)

    print("\n=== THE BREATH (steps 1-2 run, step 3 suspends) ===")
    _breath(kernel, intent_id)

    pending = outcome.get("pending_approvals", [])
    print("\n   orchestra status:", outcome["status"])
    print("   orders placed so far:", len(broker.orders), "(ZERO until you approve)")

    print("\n=== conductor approves the final order ===")
    final = orchestra.approve(intent_id, pending[0]["task_id"], approver="conductor")
    print("   final status:", final["status"])
    for ts in final["task_summary"]:
        print("    ", ts["task_id"], "->", ts["status"])
    print("\n   watchlist:", [r[0] for r in kernel.db.execute("SELECT key FROM watchlist")])
    print("   orders placed:", broker.orders)


if __name__ == "__main__":
    main()
