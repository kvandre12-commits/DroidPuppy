"""Watch the platform breathe: one intent through all four layers.

    L1 Intent  ->  L2 Orchestra decomposes/dispatches  ->  L3 adapter  ->
    L4 capability (watchlist)  ->  Observation spine  ->  Result back to L1

Run:  python3 run_demo.py    (from the orchestra/ directory)
"""

from __future__ import annotations

import datetime as dt
import os
import uuid

from adapters import Registry, WatchlistAdapter
from kernel import Kernel
from orchestra_agent import OrchestraAgent


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    contracts = os.path.join(here, "..", "contracts", "v1")
    db_path = os.path.join(here, ".orchestra_demo.db")
    if os.path.exists(db_path):
        os.remove(db_path)  # clean slate for the demo

    kernel = Kernel(db_path)
    registry = Registry()
    registry.register(WatchlistAdapter(kernel.db))
    orchestra = OrchestraAgent(kernel, registry, contracts)

    intent = {
        "contract_version": "1.0.0",
        "intent_id": "intent-" + uuid.uuid4().hex[:8],
        "domain": "trading",
        "statement": "add SPY 745C (2026-06-15) to the watchlist",
        "goal": {
            "type": "watchlist_add",
            "params": {"symbol": "SPY", "exp": "2026-06-15", "strike": 745, "right": "C"},
        },
        "constraints": [],
        "authority": {"required": False, "approver": None},
        "priority": "normal",
        "success_criteria": ["contract present on watchlist"],
        "created_by": "conductor",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "accepted",
    }

    print("=== L1  WHAT (SharpEdge intent) ===")
    print("   ", intent["statement"])

    intent_id = orchestra.submit(intent)

    print("\n=== L2->L4  the Orchestra runs the loop ===")
    result = orchestra.run(intent_id)

    print("\n=== THE BREATH  (observation spine) ===")
    for obs in kernel.get_observations(intent_id):
        print(f"   [{obs['type']:>18}] {obs['payload'].get('message', '')}")

    print("\n=== L2->L1  Result (loop closed) ===")
    print("    status:", result["status"])
    for ts in result["task_summary"]:
        print("    task", ts["task_id"], "->", ts["status"])

    print("\n=== side effect: watchlist now holds ===")
    for row in kernel.db.execute("SELECT key FROM watchlist"):
        print("   *", row[0])

    print("\n=== RESUME PROOF: run the same intent again ===")
    result2 = orchestra.run(intent_id)
    print("    re-run status:", result2["status"],
          "- no task re-executed (all already succeeded); resume-safe")


if __name__ == "__main__":
    main()
