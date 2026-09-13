# Project OS Capability-Discovery Architecture (frozen)

**Status:** Frozen architecture. This document freezes the design; it does **not** implement it.
No resolver, protocol, catalog format, or tool-loading code is defined or committed here.
**Chain:** problem proved -> constraint established -> existing machinery mapped -> runtime
mechanism proved -> architecture frozen (this document).

**Reads with:**
- [`ANDROID_CAPABILITY_PLANE_DRIFT.md`](./ANDROID_CAPABILITY_PLANE_DRIFT.md) - evidence / problem
  receipt: advertised capability exceeded executable capability on Android (silent skip, no
  reconciliation).
- [`CAPABILITY_DISCOVERY_BOUNDARY.md`](./CAPABILITY_DISCOVERY_BOUNDARY.md) - the forward-looking
  design constraint this architecture satisfies (three-plane refinement, anti-goal, `UNAVAILABLE`
  as first-class).

---

## Verified implementation assumption (the last hole, now closed)

The final missing assumption behind the general-case design has been verified read-only:

- Pinned **`pydantic-ai-slim==2.35.0`** provides **`DynamicToolset(toolset_func, per_run_step=True)`**
  (`pydantic_ai/toolsets/_dynamic.py`, registered via the agent `toolset` decorator into
  `Agent._dynamic_toolsets`). With `per_run_step=True` (the default), the toolset function is
  **re-evaluated on each run step**, so the executable toolset - and therefore the tool schemas the
  model sees - can change **between model steps within a single active run**, without reconstructing
  the agent.
- Supporting native mechanisms in the same pinned version: per-run `toolsets=` on
  `run/run_sync/run_stream/iter` ("additional toolsets for this run", additive), the
  `override(toolsets=...)` context manager, and mutable `FunctionToolset.add_tool/add_function`.
- Conversation history is external to the `PydanticAgent` (Code Puppy passes
  `run(message_history=agent._message_history)`), so agent reconstruction between turns is
  history-safe - available as a fallback, not required.

**Code Puppy does not currently use any of these dynamic mechanisms.** Today it freezes the
model-visible tool set at agent construction (static two-pass build in
`code_puppy/agents/_builder.py`; `run()` is called with no `toolsets=`). This document identifies an
**existing upstream Pydantic-AI primitive that could support** the architecture; it does **not**
describe an already-wired Code Puppy feature.

---

## The architecture

```
Normal turn
-----------
Code Puppy
  |
  |-- tiny permanent control surface
  |     `-- capability discovery
  |           `-- DynamicToolset (re-evaluated per run step)
  `-- currently resolved tools: none / minimal


User asks for something requiring Android
-----------------------------------------
Code Puppy
  `-- discovers: "I need Android browser navigation"
        v
      Project OS resolver
        v
      DroidPuppy provider claims the supported capability
        v
      resolved state changes
        v
      DynamicToolset re-evaluates on next model step
        v
      ONLY the relevant real DroidPuppy tool schemas appear
        v
      Puppy uses them normally
```

No ~40-50 DroidPuppy tools every turn. No `invoke_capability(capability, args)` megatool. No
rebuilding the agent to expose a tool. No pretending Android operations carry Playwright semantics
they do not possess.

---

## Frozen decisions

1. **Small permanent discovery/control surface, not provider tool injection.** The permanently
   model-visible surface is a minimal discovery affordance. Providers are not injected wholesale into
   every turn.

2. **Large discoverable universe, tiny per-turn surface.** A provider may offer a large discoverable
   capability universe without placing all corresponding tool schemas in every model turn.

3. **General-case: just-in-time real tools.** Discovery resolves the required capability/provider and
   makes the provider's **real native tool schemas** available just in time - the model then calls
   them normally, with their genuine schemas.

4. **Verified runtime primitive.** `DynamicToolset(per_run_step=True)` in the pinned
   `pydantic-ai-slim==2.35.0` is the presently verified runtime primitive capable of re-evaluating
   the executable surface between steps of an active run. Recorded as the **current implementation
   primitive**, not as permanent architectural ownership or an API commitment. If the upstream API
   changes, the architecture stands; the primitive is replaceable.

5. **Below-model pre-resolution is an allowed optimization.** When the required intent is already
   known (e.g. agent role or task class), resolution may occur below the model so the model sees only
   the resolved native tools - using the **same resolution semantics** as the general case.

6. **Reject a generic `invoke_capability` megatool.** Funneling every operation through one generic
   wrapper reintroduces indirection and semantic loss. Rejected.

7. **Preserve provider semantics; never manufacture equivalence.** Real semantic operations (e.g.
   Playwright `browser_find_by_role`) must never be silently satisfied by coarse ones (e.g. an
   Android coordinate tap). Providers keep their real semantics.

8. **Resolution is fail-closed; `UNAVAILABLE` is first-class.** If a capability cannot be resolved
   and verified, nothing is bound for it and the honest result is `UNAVAILABLE` - never a silent
   skip, never a full-surface leak, never false equivalence.

### Preserved invariant

```
advertised capability
  (subset of) currently resolved executable capability
    (subset of) discoverable capability universe
```

---

## Ownership boundary

- **Project OS** owns the capability vocabulary, the provider contract, and the resolution semantics
  (candidate selection, fail-closed behavior, `UNAVAILABLE`). Engine-level and **not
  Android-specific** - the same boundary governs any provider (browser backends, brokers, GitHub,
  Code Puppy's own tool collection).
- **Code Puppy** owns host / binding mechanics - how resolved tools are surfaced to the running
  agent (the dynamic-toolset wiring, the always-visible discovery affordance, the assembly of the
  executable set before Pydantic-AI receives it).
- **DroidPuppy** owns Android capabilities as **one discoverable provider**. Its tools stay behind
  the discovery boundary and surface only when an intent resolves to a class it claims.
- **Domain systems (e.g. SharpEdge)** retain their own domain truth; they are providers/consumers
  under the same boundary, not owners of it.

---

## Rejected alternatives

- **Inject all provider tools every turn.** The original anti-goal. Trades a capability-mismatch
  defect for context-bloat and tool-selection defects; the ~40-50 DroidPuppy tools do not belong in
  every model turn.
- **`discover_capabilities` + generic `invoke_capability`.** Two permanent tools where one affordance
  suffices; the generic invoker flattens real per-tool schemas into `(capability, args)`, losing
  argument validation and tool-specific affordances - the same semantic loss the drift receipt warns
  against.
- **MCP-only resolution.** MCP's catalog/registry/opt-in-binding/toolset lifecycle is an excellent
  reference prototype, but binding Project OS to MCP would make it accidentally MCP-shaped and blind
  to native, plugin, UC, and adapter providers. Resolution must be provider-agnostic.
- **Fake semantic aliases** (e.g. aliasing `browser_find_by_role` onto an Android tap). Rejected -
  it manufactures equivalence between capabilities that are not equivalent.
- **Relying on the two-pass builder for mid-run binding.** The `_builder.py` two-pass construction is
  a **build-time** mechanism only; it cannot change the model-visible surface mid-conversation.
  Mid-run binding relies on `DynamicToolset(per_run_step=True)`, not the two-pass builder.

---

## Architecture vs. current implementation (explicit)

- This is **architecture**, frozen. It commits to no code.
- **Code Puppy does not currently wire Project OS resolution to `DynamicToolset`.** No resolver
  exists; no dynamic toolset is registered; `run()` is invoked without per-run `toolsets=`.
- The next step is a separate session defining the **smallest vertical implementation experiment**,
  not further architecture exploration.
