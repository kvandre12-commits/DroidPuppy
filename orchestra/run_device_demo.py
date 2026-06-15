"""Full circle: the Orchestra commands DroidPuppy to act on the real device.

L1 says "open the SharpEdge cockpit." The Orchestra Agent coordinates, picks the
DroidPuppy adapter, and L3 executes a real `am` launch on the phone. The same
control loop as the watchlist demo - but this time it touches hardware.

Run:  python3 run_device_demo.py    (from the orchestra/ directory)
"""

from __future__ import annotations

import datetime as dt
import os
import sys
import uuid

from adapters import DroidPuppyAdapter, Registry
from kernel import Kernel
from orchestra_agent import OrchestraAgent


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    contracts = os.path.join(here, "..", "contracts", "v1")
    db_path = os.path.join(here, ".orchestra_device_demo.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    # default target: the cockpit we built earlier; override via argv[1]
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8780/cockpit.html"

    kernel = Kernel(db_path)
    registry = Registry()
    registry.register(DroidPuppyAdapter())
    orchestra = OrchestraAgent(kernel, registry, contracts)

    intent = {
        "contract_version": "1.0.0",
        "intent_id": "intent-" + uuid.uuid4().hex[:8],
        "domain": "android_automation",
        "statement": f"open {url} in Brave on the device",
        "goal": {
            "type": "open_url",
            "params": {"url": url, "browser": "com.brave.browser"},
        },
        "constraints": [],
        "authority": {"required": False, "approver": None},
        "priority": "normal",
        "success_criteria": ["Brave launched to the URL"],
        "created_by": "conductor",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "accepted",
    }

    print("=== L1  WHAT (intent) ===")
    print("   ", intent["statement"])

    intent_id = orchestra.submit(intent)

    print("\n=== L2->L3  Orchestra -> DroidPuppy (real device action) ===")
    result = orchestra.run(intent_id)

    print("\n=== THE BREATH (observation spine) ===")
    for obs in kernel.get_observations(intent_id):
        print(f"   [{obs['type']:>18}] {obs['payload'].get('message', '')}")

    print("\n=== L2->L1  Result ===")
    print("    status:", result["status"])
    for ts in result["task_summary"]:
        print("    task", ts["task_id"], "->", ts["status"])


if __name__ == "__main__":
    main()
