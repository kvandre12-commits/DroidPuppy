# Platform Substitution Thesis

## Executive claim

DroidPuppy does not primarily compete with other agent systems on the number of
capabilities advertised. It challenges **how capabilities are delivered**.

Two systems may both claim browser control, repository access, screenshots,
search, and workflow execution while imposing radically different operational
costs. Capability count hides those costs. Delivery architecture exposes them.

The central distinction is:

```text
Framework expansion
New capability -> more framework dependencies -> larger environment

Platform substitution
New requirement -> existing native capability -> bounded adapter
```

The June Android port is evidence for the second approach. Desktop browser
handoff depended on Playwright and its browser assumptions. Android already had
an application router and a capable installed browser. DroidPuppy replaced the
incompatible actuator rather than reproducing the desktop stack:

```text
Desktop path
agent -> browser abstraction -> Playwright -> bundled/managed Chromium

Android path
agent -> bounded Android adapter -> intent -> installed Brave
```

The intelligence did not require a desktop browser engine. It required a safe,
observable way to satisfy the user's intent on the actual platform.

## Why this matters

### Deployability

Every mandatory framework dependency adds compatibility conditions: operating
system, architecture, interpreter version, native wheels, compiler toolchain,
network availability, package indexes, and transitive version constraints.
Platform substitution starts with capabilities already proven by the device and
adds only the smallest adapter needed to expose them.

### Security

A larger dependency graph creates more code provenance, update channels, import
side effects, credential integrations, and supply-chain trust decisions. A
bounded adapter does not eliminate security risk, but its authority and behavior
are easier to enumerate and audit.

### Recoverability

Framework expansion often makes recovery equivalent to reconstructing the
entire dependency environment. Platform substitution lets the engine and the
platform overlay have separate identities, checksums, tests, and rollback
points. A broken adapter need not trigger an engine replacement.

### Comprehensibility

A capability is governable only when operators can explain what performs the
action. "Open this URL" is comprehensible when it becomes an Android intent to
a named package. It becomes harder to reason about when it activates a browser
framework, downloaded runtime, profile manager, automation protocol, and plugin
chain merely to hand a URL to a browser already present on the device.

### Efficiency

Native substitution can reduce installation work, disk use, startup imports,
and background processes. It does not automatically prove lower model-token use
or better task completion. Those remain measurements, not slogans.

## The protected baseline

`june-brave-v1` encodes the original boundary:

- reuse an existing working Code Puppy engine;
- install no engine or Python package;
- install no compiler or Termux build tool;
- expose seven original Android actuator plugins;
- use native Brave intent handoff as the base browser path;
- keep ADB/CDP as an advanced platform capability;
- reject silent implementation or dependency expansion.

This is not a claim that the June implementation is eternally sufficient. It is
a preserved control specimen: a small, operational architecture against which
successors can be tested.

## Comparison discipline

Feature matrices reward accumulation. A useful comparison must include delivery
cost and authority:

| Question | Framework expansion | Platform substitution |
|---|---|---|
| How is a capability added? | Add framework/package/provider integration | Adapt an existing platform primitive |
| What changes at install time? | Dependency graph and often native artifacts | Bounded overlay files |
| What must be trusted? | Framework plus transitive supply chain | Engine, adapter, and named platform service |
| What breaks across platforms? | Framework assumptions and binary availability | Adapter implementation |
| What is the rollback unit? | Often the whole environment | The bounded adapter/baseline |
| Is absence acceptable? | Frequently converted into mandatory support | Capability can remain explicit and optional |
| How is authority explained? | Through layered framework abstractions | Through the platform operation actually invoked |

Neither column is universally correct. A framework is justified when it
provides behavior the platform cannot supply, materially improves correctness,
and survives qualification on target devices. Substitution is justified when
the platform already performs the needed action and another framework would
mostly duplicate it.

## Decision rule

Before adding an agent dependency, ask in order:

1. What user outcome is required?
2. Does the target platform already provide that outcome?
3. Can a narrow adapter expose it with explicit authority and evidence?
4. What behavior would a framework add that the native path cannot?
5. Is that additional behavior required now?
6. Has the framework been tested on every claimed target platform?
7. Can it remain optional and fail gracefully?
8. What is the independent rollback path?

If questions 2 and 3 are yes while question 5 is no, adding the framework fails
YAGNI and expands the attack surface without earning its keep.

## What we are challenging

We challenge these assumptions:

- More integrations necessarily mean a more capable system.
- A capability is portable because its Python API is portable.
- Optional behavior should be installed for everyone so it is always available.
- A framework abstraction is safer than a native primitive by default.
- Upgrading the engine is the normal response to a platform mismatch.
- Reproducibility means a lockfile even when the lock resolves unbuildable
  artifacts on the target platform.

Our alternative is:

- preserve a small known-working engine;
- attach platform capabilities through explicit overlays;
- qualify each overlay on real target hardware;
- keep advanced behavior optional;
- freeze evidence-backed baselines;
- create new baseline identities instead of mutating old evidence;
- measure outcomes rather than advertise dependency-backed potential.

## Honest limits

Platform substitution is not magic minimalism.

- Android intents provide handoff, not full DOM automation.
- ADB and CDP introduce their own permission and lifecycle boundaries.
- Native platform APIs can change across vendors and OS releases.
- An in-process policy callback is not a security sandbox.
- Reusing an existing engine inherits that engine's vulnerabilities.
- A frozen baseline can fossilize defects and must not replace a qualified
  security-maintenance lane.
- Smaller installation size does not prove better reasoning, code quality, or
  token efficiency.

These limits strengthen the thesis because they identify when expansion may be
justified instead of treating minimalism as a religion.

## Falsifiable evaluation

The thesis should be tested against alternative agents using the same hardware,
model where possible, and task set. Measure:

- packages resolved and artifacts built from source;
- bytes downloaded and installed;
- time to first successful action;
- idle memory and startup time;
- prompt and tool-schema size;
- provider requests and retries per completed task;
- task success and correctness;
- permissions and credential exposure;
- failure isolation;
- offline recovery and rollback;
- operator ability to identify exactly what executed.

Platform substitution wins only when it delivers the required outcome with less
operational cost or clearer authority **without unacceptable capability loss**.
That is a testable engineering claim.

## Position

DroidPuppy's reason to exist is not that Android deserves a smaller imitation
of a desktop agent. It exists because constrained, heterogeneous platforms
reveal a general architectural truth:

> The best agent capability is not always another framework. Sometimes the
> platform already knows how to do the work, and intelligence means choosing the
> smallest honest adapter that lets it.

That principle applies beyond Android—to edge devices, workstations, managed
enterprise environments, local inference hosts, and any system where deployment
and recovery matter as much as a demo.
