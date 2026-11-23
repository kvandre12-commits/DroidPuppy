# Code Puppy 1.0 / Pax Architecture Study

**Permanent project letter**  
**Date:** 2026-11-22  
**From:** SharpEdge  
**For:** Kurtis and the DroidPuppy/SharpEdge project record

## Why this note exists

Code Puppy 1.0 changes more than a dependency. It changes who owns the runtime.
The examined `1.0.0rc1` tree explicitly describes Code Puppy as a distribution
of `pydantic-ai-pax`: Pax owns the agent loop, terminal UI, sessions, models,
MCP, plugins, workspaces, and most tool behavior. Code Puppy supplies identity,
personality, migration, update policy, and partial compatibility with 0.0.x.

This study asks two separate questions:

1. Why is that decision rational for upstream Code Puppy?
2. Why is wholesale Pax adoption a poor default for DroidPuppy and SharpEdge?

The answer is not "Pax bad." The systems optimize for different outcomes.
Upstream is reducing duplicated runtime maintenance and maximizing immediately
available capability. We prioritize target-qualified operation, bounded
authority, token and dependency discipline, Android survivability, and
independent recovery.

## Executive conclusion

Upstream's decision is understandable. Its old implementation carried a very
large locally maintained runtime and test surface while overlapping heavily
with Pydantic AI, Harness, and Pax. Moving the runtime upstream can reduce Code
Puppy's maintenance burden and inherit improvements in caching, workspaces,
plugins, sessions, models, sandboxes, and cross-platform support.

It is nevertheless the wrong default architecture for us because the examined
v1 implementation:

- deliberately installs every Pax extra;
- requests nine provider or sandbox extras whether the operator needs them or
  not;
- resolves a 185-entry lock graph with five Git sources in the measured tree;
- produced Android native-source-build pressure and did not complete its local
  Termux bootstrap;
- has no Android/Termux qualification in the searched v1 rewrite tests or plan;
- replaces numerous Pax internals at startup because a distribution identity
  seam does not yet exist;
- externalizes runtime size rather than eliminating it;
- supports only 15 of 77 legacy hooks, while 62 register but do not fire;
- had unfinished JSON-agent, native-plugin, documentation, and hardening work;
- treats absent optional support as a packaging failure rather than an honest,
  acceptable state.

Our decision is therefore:

> Study and selectively borrow Pax mechanisms, but do not make Pax the
> mandatory SharpEdge/DroidPuppy runtime. Preserve a stable engine boundary and
> attach default-off, target-qualified platform adapters whose operational value
> earns their cost.

## What changed in Code Puppy 1.0

The v1 contributor guide states its architectural rule directly:

> Code Puppy 1.0 is a distribution of `pydantic-ai-pax`.

The local entry point installs Code Puppy-specific replacements and then calls
Pax's CLI. The effective shape is:

```text
pydantic-ai-pax runtime
    + Code Puppy branding and personality
    + migration from 0.0.x
    + update behavior
    + legacy session import
    + partial plugin-compatibility bridge
```

It is not merely:

```text
Code Puppy runtime + optional Pax capability
```

This matters because core behavior, compatibility, release risk, and platform
support now depend on Pax's contracts and implementation choices.

## Why upstream made the move

### 1. A very large maintenance surface

The rewrite plan measured approximately:

| Surface | Approximate size before the rewrite |
|---|---:|
| `code_puppy/` | 97,239 lines |
| tests | 119,637 lines |
| `code_puppy_core_plugins` non-test code | 58,000 lines |

The initial distribution rewrite commit, `6a6a1d85`, reported:

```text
826 files changed
1,752 insertions
222,143 deletions
```

A repository-level Python-line check found approximately:

```text
Before rewrite: 216,933 source/test lines
Initial rewrite: 1,358 source/test lines
Examined merged v1 tree: 7,646 source/test lines
```

This is a legitimate maintenance reduction for Code Puppy's maintainers.

### 2. Removal of duplicated runtime machinery

The old project maintained substantial implementations for:

- terminal UI and rendering;
- tools and tool registration;
- agent orchestration;
- sessions and history;
- MCP lifecycle;
- model/provider plumbing;
- plugin lifecycle;
- workspaces and shell behavior;
- caching, speculation, and compaction behavior.

Pax and Harness provide much of this. Depending on them avoids maintaining
parallel implementations.

### 3. Inheriting upstream fixes and capabilities

A Pax distribution can inherit work on:

- cache-stable agent behavior;
- deferred loading and tool search;
- speculative execution;
- model and provider support;
- workspace implementations;
- session import and persistence;
- sandbox providers;
- Windows support.

For a small upstream team, concentrating on product identity and migration while
another project owns the runtime can be rational.

### 4. A uniform batteries-included product

The v1 implementation deliberately requires every extra Pax offers. The
corresponding test fails when Pax adds a new extra that Code Puppy has not yet
required. The stated goal is that no Code Puppy command answers that provider
support is not installed.

That is coherent for a product prioritizing broad, immediately available
cloud/desktop capability. It simply is not our priority.

## Why the move is not suitable for us

### 1. Mandatory optionality violates YAGNI

The examined v1 dependency requests these Pax extras:

```text
boxd
daytona
e2b
kubernetes
modal
opensandbox
render
sprites
typesafe
```

The rewrite plan reports that enabling every extra added 62 packages and about
140 MB in one Windows measurement. Our offline delivery benchmark found 185
entries in the v1 lock graph and five Git sources.

The benchmark does not claim all 185 entries install in every profile. It does
show that six direct dependency declarations conceal a much larger resolved
surface, and the v1 policy explicitly makes all Pax extras mandatory.

Our rule is different:

> If an operator did not request a provider or sandbox, its support should not
> be installed merely to avoid saying that it is absent.

Absence is not a product defect when the capability is optional. Honest absence
is safer than imaginary universality.

### 2. The smaller local repository is not the whole deployed system

The merged v1 `code_puppy/` tree measured about 133 KB locally, but the rewrite
plan estimated Pax itself at roughly 68,000 lines before counting Harness,
Pydantic AI, Monty, provider SDKs, and transitive packages.

The rewrite genuinely reduces **Code Puppy-owned maintenance code**. It does not
make the complete operational system 133 KB. Most runtime implementation moved
across a package boundary.

Therefore:

```text
less locally owned code != smaller installed system
```

### 3. The dependency policy already failed our Android bootstrap

On the local Android/Termux target, resolving and synchronizing the examined v1
tree attempted native source builds including:

- `grpcio`;
- `cryptography`;
- `pydantic-core`;
- `jiter`;
- `tiktoken`;
- `pillow`.

The bootstrap did not complete before the agent session died. This does not
prove Pax can never run on Android. It proves the examined v1 policy is not a
qualified replacement for our working phone runtime.

No Android, Termux, or AArch64 qualification cases were found in the searched v1
rewrite tests or rewrite-plan documentation.

### 4. Runtime ownership moved outside Code Puppy

Pax owns the loop, UI, tools, sessions, models, plugin lifecycle, and workspace
behavior. Code Puppy customizes it by replacing internal names across many Pax
modules at startup, including configuration paths, credential internals, update
behavior, branding, themes, plugin tuples, stock-agent construction, session
imports, and plugin discovery.

Contract tests detect when upstream moves those names. That is responsible, but
it also reveals the missing architectural seam. The rewrite plan describes each
replacement as debt pending an upstream identity hook.

Our preferred relationship is:

```text
stable engine contract
    -> bounded adapter
    -> explicit target qualification
```

The examined v1 relationship is closer to:

```text
upstream runtime internals change
    -> distribution replacement contract breaks
    -> Code Puppy must follow upstream
```

### 5. Compatibility is partial and sometimes silent

The 0.0.x callback system exposed 77 hooks. In the examined v1 compatibility
layer:

```text
15 hooks are supported and fire
62 hooks register but do not fire
```

A plugin may therefore load without crashing while part of its behavior has
disappeared. Other documented gaps included:

- JSON agents not built;
- `/agent` behavior not built;
- native plugin ports not started;
- phases 4 through 6 unfinished;
- README and docs not fully rewritten;
- i18n dropped;
- ACP dropped;
- sub-agent transcripts not migrated;
- delegated sub-agents not receiving Puppy personality.

This is a rewrite with a compatibility membrane, not proven feature parity.

### 6. The examined RC used unreleased upstream sources

The measured tree used five packages from one pinned Pydantic AI Git commit:

```text
pydantic-ai-pax
pydantic-clai2
pydantic-ai-harness
pydantic-ai-slim
pydantic-graph
```

A fixed commit is better than floating `main`, but a Git-source runtime still
introduces retrieval, wheel, build, and long-term recovery concerns. The v1 plan
itself marked this state as not publishable until released packages replaced the
sources.

### 7. Every installed provider expands qualification work

Package count alone does not prove insecurity. It is still operationally
relevant because every installed provider may add:

- authentication and credential paths;
- network clients;
- transitive packages;
- import behavior;
- update and advisory obligations;
- platform assumptions;
- recovery requirements.

Our security and efficiency rule is that code must earn its presence through an
approved, measured requirement.

## Architecture comparison

| Question | Code Puppy v1 / Pax | SharpEdge / DroidPuppy |
|---|---|---|
| Runtime ownership | Pax owns nearly everything | Preserve a qualified engine boundary |
| Capability policy | Install every offered extra | Default off; qualify per target |
| Portability strategy | Framework abstraction first | Actual platform primitive first |
| Android strategy | Reconstruct the framework graph | Substitute native Android actuators |
| Missing optional capability | Packaging problem | Honest, nonfatal state |
| Upgrade unit | Runtime dependency graph | Engine and overlays independently |
| Identity | Personality and branding over Pax | Portable identity independent of runtime |
| Recovery | Rebuild the pinned environment | Restore known engine plus bounded overlay |
| Main strength | Reduced upstream maintenance | Deployability, authority clarity, recovery |

## What we should borrow

Rejecting wholesale adoption does not mean rejecting useful engineering.
Candidates for selective adoption or independent reproduction include:

1. **Deferred tool loading** to limit prompt and runtime surface.
2. **Cache-stable prompt construction**, measured with the same model and task.
3. **Typed workspace contracts** behind narrow adapters.
4. **Explicit plugin declarations** instead of uncontrolled discovery.
5. **Non-destructive migration** with dry-run support.
6. **Contract tests** at every external dependency boundary.
7. **Release-candidate isolation** that protects stable users.

The rule is:

> Borrow mechanisms, not the whole dependency policy.

## Capability growth is the purpose, not the enemy

The runtime-adoption gate is deliberately narrow. It governs changes that
replace the qualified engine boundary or make an entire framework/provider
family mandatory. It must never be used to freeze the capability graph.

SharpEdge and DroidPuppy should actively expand through the already-frozen
three-plane architecture:

```text
tiny permanent control surface
    -> large discoverable capability universe
    -> just-in-time binding of relevant real native tools
```

That gives the agent more reach without injecting every tool schema into every
turn or granting every provider permanent authority. Bounded overlay
capabilities, default-off providers, platform-native adapters, isolated
experiments, and new immutable candidate assessments are explicitly outside the
runtime gate's prohibition.

The desired direction is therefore:

```text
capability graph: broad and growing
per-turn tool surface: narrow and relevant
installed authority: bounded and explicit
runtime ownership: stable and replaceable only by evidence
```

Minimalism is a delivery discipline, not a vow of incapability. The overlay is
the attachment plane through which the system grows without surrendering its
identity, recovery boundary, or target fitness.

## Adoption gate

Pax should not become a mandatory runtime unless a minimal profile proves all of
the following on real targets:

1. Core installation does not require unrelated sandbox-provider extras.
2. Android/Termux installation is reproducible without uncontrolled source
   builds.
3. The same required tasks succeed using the same model where possible.
4. Startup memory and latency are acceptable.
5. Prompt and tool-schema costs are measured.
6. Provider requests, retries, and context do not amplify materially.
7. Platform-native adapters remain first-class.
8. Authority is clearer or stronger, not merely more abstract.
9. Engine and actuator layers retain independent rollback.
10. Missing optional support remains an honest, nonfatal state.
11. Security maintenance and provenance can be reproduced offline.
12. The capability gain exceeds its dependency, token, and operational cost.

The examined v1 tree does not pass this gate for our Android target.

## Machine-enforced action

This gate is now executable rather than advisory:

```bash
python scripts/evaluate_runtime_candidate.py
```

The evaluator combines:

```text
baselines/runtime-adoption-policy-v1.json
evidence/benchmarks/pax-v1-adoption-assessment-20261122.json
```

It fails closed unless every required gate has an evidence-backed `pass`.
`fail` and `unmeasured` both refuse qualification; missing, unexpected, or
malformed gates make the assessment invalid. Exit codes are:

```text
0  candidate qualified
1  valid assessment, qualification refused
2  invalid policy or assessment
```

The current Pax v1 assessment is intentionally refused. This does not blacklist
Pax forever: a new immutable assessment may qualify a narrower successor after
all measurements pass. It prevents enthusiasm, package availability, or a
smaller local repository from silently becoming architectural approval.

## Evidence boundary

This study is grounded in the locally preserved v1 tree at merge commit
`6ac4efa3`, including:

- `AGENTS.md`;
- `pyproject.toml` and `uv.lock`;
- `docs/upgrade/code_puppy_1_0_rewrite_plan.md`;
- `code_puppy/main.py`;
- `code_puppy/distribution.py`;
- `code_puppy/builtin_plugins.py`;
- `tests/test_optional_support.py`;
- `tests/test_distribution_contract.py`;
- rewrite commit `6a6a1d85`;
- all-extras commit `be2c2178`.

Delivery-surface figures come from:

```text
evidence/benchmarks/delivery-surface-local-20261122.json
```

Receipt SHA-256:

```text
f4efc211fedbed17b899d56ba99237b98804551c8d261d840959e861a508907c
```

The benchmark performs no package installation, network request, provider
request, or target mutation. Lock-graph size is a deployment and qualification
signal; it does not independently prove security, task quality, token
efficiency, or installed-package count for every profile.

## Final position

Pax addresses upstream's maintenance problem by centralizing runtime ownership
and maximizing installed capability. Our problem is different: safe, lean,
recoverable operation on constrained real devices.

```text
Code Puppy v1 / Pax
    upstream runtime
    + every offered capability installed
    + framework-defined portability
    + partial compatibility shims

SharpEdge / DroidPuppy
    stable engine boundary
    + only required capabilities
    + native platform substitution
    + evidence-backed qualification
    + independent rollback
```

Our position is therefore precise rather than tribal:

> Pax may contain valuable mechanisms, but wholesale Pax adoption optimizes the
> wrong objective for us. A capability joins SharpEdge only after it earns its
> security, dependency, token, and operational cost on the real target.

That is not fear of growth. It is freedom from growth that cannot justify
itself.
