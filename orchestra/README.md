# Orchestra (the working platform)

The Orchestra Agent and its substrate - a runnable implementation of the
architecture in `../docs/ORCHESTRA_AGENT.md`, governed by the contracts in
`../contracts/v1/`.

```
L1 Intent  ->  L2 Orchestra Agent  ->  L3 Adapters  ->  L4 Capabilities
                        |
                     Kernel (durable, resumable state)
```

## Files

| File | Role |
|------|------|
| `kernel.py` | Durable SQLite state substrate (intents/tasks/observations/results). Makes the Orchestra resumable. |
| `adapters.py` | L3 adapters behind one contract: `WatchlistAdapter` (idempotent), `DroidPuppyAdapter` (real `am` device actions), `MockBrokerAdapter` (irreversible). Plus the `Registry`. |
| `planners.py` | Pluggable domain decomposition. Register a planner per goal type; the Orchestra core stays domain-free. |
| `orchestra_agent.py` | The sole coordinator: submit, decompose, route, manage handoffs, maintain state, observe, recover, report - plus `approve`/`deny`. |
| `run_demo.py` | Intent -> database (watchlist). The first breath. |
| `run_device_demo.py` | Intent -> real device (opens a URL in Brave). Proves pluralized L3. |
| `run_approval_demo.py` | Irreversible order suspends until approved/denied. "You own every trade." |
| `run_pipeline_demo.py` | One intent -> 3-step DAG across 3 adapters, ending on an approval gate. Proves the generalized planner. |

## Run

```bash
cd orchestra
python3 run_demo.py
python3 run_device_demo.py        # opens Brave on the device
python3 run_approval_demo.py
python3 run_pipeline_demo.py
```

(Imports are absolute, so run from inside `orchestra/`. Requires `jsonschema`.)

## Properties demonstrated

- **Contract-compliant** - every intent/task/observation/result is validated
  against `../contracts/v1` before it is trusted.
- **Durable + resumable** - state lives in the kernel; re-running an intent
  never re-does completed work.
- **Pluralized L3** - same Orchestra drives a database, the device, and a broker
  by swapping adapters. Stack-agnostic, demonstrated.
- **Generalized planning** - add a domain by registering a planner, never by
  editing the Orchestra core.
- **Safe recovery** - only `read`/`idempotent` tasks auto-retry; `irreversible`
  never does.
- **Human authority** - `requires_approval` tasks suspend at `awaiting_approval`
  until `approve()`; `deny()` aborts them. Money cannot move without a yes.

## Build status

Build-order items 1-6 from `../docs/ARCHITECTURE_REVIEW.md` are complete.
Next horizons: a real broker adapter (e.g. Robinhood) behind the approval gate,
concurrency + resource locks, and a contract-versioning policy in practice.
