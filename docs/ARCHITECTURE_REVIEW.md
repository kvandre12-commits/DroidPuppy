# SharpEdge Architecture Review

> A principal-engineer evaluation of the Orchestra Agent constitution
> (see `ORCHESTRA_AGENT.md`). Critical by request. This is the engineering
> half: strengths, failure modes, contracts, schemas, and a build order.

---

## Strengths

- **Negative-space definitions.** Every layer is defined by what it refuses to
  do. This pre-empts the most common failure of layered systems: responsibility
  bleed. It is the strongest property of the design.
- **Orchestration over choreography.** A sole coordinator keeps observability
  and recovery tractable. Event-choreographed systems become undebuggable.
- **Capabilities are deliberately dumb** ("don't know WHY"). Single
  Responsibility at system scale: testable, reusable, swappable.
- **The kernel is first-class.** Shared state/contracts modeled as a substrate
  beneath the layers, not bolted on later.
- **Domain coupling isolated to L1.** Everything below is generic by
  construction. This makes "stack-agnostic" real, not aspirational.
- **Convergent with proven patterns** - control plane vs data plane,
  planner/orchestrator/executor/tools, workflow engines, the saga pattern.

## Failure modes (the seams to fix)

1. **Sole coordinator = SPOF + throughput ceiling.** "Sole" must mean *sole per
   execution context*, not a global singleton. The Orchestra needs durable
   state so it RESUMES (not restarts) after a crash, and step execution must be
   idempotent so resume does not double-fire.
2. **L3 is wrongly singular.** A trading order goes Orchestra -> MCP capability
   and never touches DroidPuppy. Generalize L3 into a *set of execution
   adapters* (DroidPuppy = Android, MCP = broker, plus cloud/TV/research) behind
   one uniform Adapter contract. DroidPuppy is one adapter, not the layer.
3. **"HOW" is overloaded across L2 and L3.** Split it: L2 = cross-adapter
   coordination (which adapter, what sequence, handoffs between them); L3 =
   within-adapter execution sequencing (a device macro). Name the split or
   ownership of retries/sequencing is ambiguous.
4. **Decompose-vs-domain-analysis contradiction.** L2 must "decompose intent"
   but is forbidden "domain analysis." You cannot decompose "reduce chicken
   waste" without domain reasoning. Resolution: the Orchestra does *structural*
   decomposition (builds the task DAG) and delegates *domain* decomposition to a
   planning capability owned by L1's domain. Name that planning step.
5. **Recovery is unsafe without a side-effect model.** You cannot blindly retry
   "place order." Every capability must declare a side-effect class
   (read | idempotent | nonidempotent | irreversible) and, where needed, a
   compensation (undo). Recovery branches on that class.
6. **No human-authority model - and trading is in scope.** Irreversible/financial
   actions need a first-class approval gate (task status `awaiting_approval`
   that suspends the DAG). This is the "you own every trade" principle.
7. **The kernel can rot into a blackboard.** Layers must communicate through
   contracts and access the kernel via defined operations, not free reads/writes,
   or it becomes global mutable state with extra steps.
8. **No concurrency or contract-versioning model.** Need resource locks for
   shared resources (accounts, devices) and versioned contracts with a
   compatibility policy.

## Contracts between layers

| Edge | Contract | Purpose |
|---|---|---|
| L1 -> L2 | Intent | declarative goal + constraints + authority |
| L2 -> L3 | Task / Dispatch | one executable unit, typed, side-effect class |
| L3 -> L4 | Capability Invocation | typed call + auth scope |
| L4/L3 -> kernel | Observation | progress, metrics, violations, stalls |
| L2 -> L1 | Result | closed-loop outcome |
| any <-> kernel | Kernel Access | state via ops, not free reads |
| cross-cut | Approval/Authority | suspends a task pending authorization |

The **Handoff** is where "contract-compliant" is enforced: task A's output is
validated against task B's input schema *before* B runs. No validation, no
handoff.

## Build order (highest leverage first)

1. The five schemas as versioned JSON Schema (this commit) - the load-bearing wall.
2. Kernel MVP - SQLite + a contract-typed access API (not a blackboard).
3. Orchestra vertical slice - one intent -> one task -> one adapter -> result,
   durable + resumable. Hardcode the decomposition; do NOT build a general
   planner yet.
4. Adapter protocol + one real adapter wrapping an existing capability.
5. Approval gate - non-negotiable because trading is in scope.
6. Then generalize the planner and add a second domain.

## Scaling across domains

- Keep L1 the only domain-coupled layer. New domain = new intent producer + a
  domain planner capability; everything below is reused.
- Pluralize L3 into adapters behind one contract.
- Capability registry with declared contracts + side-effect classes.
- Per-domain policy as config (allowed capabilities, approval rules, risk
  limits), not code.
- Concurrency scoped per execution context + kernel resource locks.
- Versioned contracts + a uniform observation/event schema (one pane of glass).

## Bottom line

The bones are sound. Three things stand between this and a real platform:
(1) the contracts/schemas must exist, (2) L3 must be pluralized into adapters,
(3) the side-effect + approval model must be added. Fix those plus the
decompose-vs-domain-analysis seam, and this stops being a diagram and becomes a
platform.
