# Capability Discovery Boundary (Project OS constraint)

**Status:** Forward-looking design constraint. **Not implemented. No code, no resolver, no tool-loading
mechanism defined here.** This records a constraint that future Project OS / Orchestra work must satisfy.
**Motivating evidence:** [`ANDROID_CAPABILITY_PLANE_DRIFT.md`](./ANDROID_CAPABILITY_PLANE_DRIFT.md) — a
confirmed defect where advertised capabilities exceeded executable capabilities on Android.
**Explicitly out of scope:** designing or building the resolver, the discovery protocol, the catalog
format, or any tool-loading mechanics. Those belong to a later architecture session that should *start*
from this constraint.

---

## The anti-goal

Do **not** repair capability mismatch by injecting every provider's tools into every turn (e.g. dumping
DroidPuppy's ~40-50 Android tools into every Code Puppy call). That trades a capability-mismatch defect for
a context-bloat and tool-selection defect. The agent should know how to **discover** capabilities, not
**carry** every capability.

## Refined invariant

The drift finding established:

```
advertised capability ⊆ resolved executable capability
```

This constraint refines it into three planes, so the invariant no longer requires advertising every
executable capability on every turn:

```
advertised capability ⊆ currently resolved executable capability ⊆ discoverable capability universe
```

## The three planes

1. **Control plane (always visible, tiny).**
   The permanent surface the model always sees is minimal — conceptually just the ability to discover and
   invoke capabilities (e.g. `discover_capabilities(...)`, `invoke_capability(...)`). Not 50 schemas.

2. **Discovery / catalog plane.**
   A provider can advertise *what capability classes it offers* ("Android browser navigation, UI
   observation, screenshots, app launching") without emitting the full JSON tool schemas into model
   context. Discovery returns only relevant candidate capabilities for the current intent.

3. **Execution plane (just-in-time).**
   Once the agent determines it needs a specific capability, only the necessary executable tool
   definitions are exposed/bound for that operation.

## Platform selection falls out of discovery

Because discovery is environment-aware, provider selection is a natural consequence rather than a hardcoded
`if android` branch:

```
intent: browser.navigate
  desktop            -> PlaywrightBrowserProvider
  phone (CDP up)     -> DroidPuppyCDPProvider
  phone (no CDP)     -> AndroidIntentBrowserProvider
  semantics missing  -> UNAVAILABLE
```

`UNAVAILABLE` is a first-class result. A provider must be allowed to decline rather than pretend
equivalence — e.g. `browser_find_by_role` (semantic) is **not** satisfiable by an Android coordinate tap.

## DroidPuppy's role under this constraint

**DroidPuppy is a discoverable capability provider, not a giant Android tool prompt.** Its ~40-50 tools
remain behind the discovery boundary and are surfaced only when an intent resolves to a capability class it
provides.

## Relationship to Orchestra / Project OS

This maps onto the existing Orchestra layering (`orchestra/README.md`,
`docs/ORCHESTRA_AGENT.md`): `L1 Intent -> L2 Orchestra Agent -> L3 Adapters -> L4 Capabilities`.

- The discovery/catalog plane is how L2 learns which **L3 providers** can serve an intent's capability class.
- The execution plane is the narrow set of **L4 capabilities** bound once a provider is chosen.
- Discovery is **engine-level, not Android-only.** The same boundary should govern SharpEdge broker
  functions, GitHub, future Coinbase tools, and Code Puppy's own large tool collection — none of which
  should inject their entire surface every turn.

## What this constraint requires of future work (not how)

- A minimal, stable control-plane surface that does not grow with the number of providers.
- A discovery mechanism that returns capability *classes/candidates* without emitting full tool schemas.
- Just-in-time binding of only the executable tools needed for the chosen capability.
- `UNAVAILABLE` as an explicit, honest outcome — never silent skip, never false equivalence.
- The refined three-plane invariant holds on every platform.
