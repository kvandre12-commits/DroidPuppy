# SharpEdge Contracts

The load-bearing wall. Every interaction between layers is governed by one of
these versioned contracts. If it isn't contract-compliant, it doesn't happen.

See `../docs/ORCHESTRA_AGENT.md` (the constitution) and
`../docs/ARCHITECTURE_REVIEW.md` (the engineering review) for context.

## The five contracts (v1)

| Schema | Edge | Role |
|--------|------|------|
| `v1/intent.schema.json` | L1 -> L2 | SharpEdge hands a declarative goal to the Orchestra Agent |
| `v1/task.schema.json` | L2 -> L3 | One executable unit, typed, with side-effect class |
| `v1/handoff.schema.json` | task -> task | The validated edge; where contract-compliance is enforced |
| `v1/observation.schema.json` | L3/L4 -> kernel | The observability spine |
| `v1/result.schema.json` | L2 -> L1 | Closes the control loop back to the decision layer |

## Design rules baked into the schemas

- **Side-effect class is mandatory on every Task** (`read | idempotent |
  nonidempotent | irreversible`). Recovery/retry logic branches on it. You
  cannot blindly retry an irreversible action.
- **Approval is first-class.** `Task.requires_approval` + the
  `awaiting_approval` status + the `approval_required` observation type form the
  human-authority gate. Irreversible/financial work suspends here.
- **Idempotency keys** let the Orchestra resume after a crash without
  double-firing.
- **Handoffs must be validated.** `Handoff.validated` is true only after the
  producer's output passes the consumer's input schema. No validation, no
  handoff.
- **Everything carries `contract_version`** so contracts can evolve without
  silent breakage. Bump the minor for additive changes, the major for breaking
  ones, and add a `v2/` directory rather than mutating `v1/`.

## Versioning

Contracts are immutable once published. Breaking changes go in a new directory
(`v2/`, ...). Producers and consumers negotiate on `contract_version`.

## Supplemental local-intake contracts

The repo can also carry bounded adjunct contracts when they support the same
Project OS doctrine without pretending to replace the core five.

Current supplemental intake seam:

| Schema | Role |
|--------|------|
| `v1/eyes_artifact.schema.json` | Validated manifest for manually surfaced local evidence dropped into the eyes inbox |
| `v1/eyes_queue_item.schema.json` | Routed queue item created from an eyes inbox artifact for downstream workers |
| `v1/eyes_worker_result.schema.json` | Typed result artifact emitted by a one-shot local worker after consuming a queue item |
| `v1/eyes_review_required.schema.json` | Minimal governance-gate artifact telling the operator a human review is required |

These let human-native access on Android become structured local work without
forcing the Orchestra to stare at the foreground forever.

## Status

v1 draft. The schemas exist before the Orchestra Agent does, on purpose: the
wall goes up before the building.
