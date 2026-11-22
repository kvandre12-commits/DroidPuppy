# DroidPuppy Benchmarking

The benchmark program tests the Platform Substitution Thesis in phases. It keeps
architectural delivery measurements separate from model quality, runtime cost,
and security claims.

## Phase 1: delivery surface

`scripts/benchmark_delivery.py` performs an offline, read-only inspection of:

- protected baseline manifests;
- exact constraints closures;
- Python project dependency declarations;
- adjacent `uv.lock` package and Git-source counts.

It makes no network request, installs nothing, imports no agent framework, and
explicitly disclaims token-efficiency and security conclusions.

Run the portable in-repository comparison:

```bash
python scripts/benchmark_delivery.py \
  --target june-brave-v1=baselines/june-brave-v1.json \
  --target android-0720=constraints/android-0720.txt
```

Local maintainers can add other checked-out Puppies without modifying them:

```bash
python scripts/benchmark_delivery.py \
  --target june-brave-v1=baselines/june-brave-v1.json \
  --target android-0720=constraints/android-0720.txt \
  --target puppy-0759=~/code_puppy_relock_0759/pyproject.toml \
  --target puppy-modern=~/audit_982/upstream_main/pyproject.toml \
  --target puppy-v1=~/code-puppy-token-proof/pyproject.toml \
  --output evidence/benchmarks/delivery-surface.json
```

The receipt records input hashes rather than treating mutable labels as
evidence. A direct dependency count and a locked transitive package count are
reported as different units and must not be casually compared as if equivalent.

## Phase 2: controlled startup

Run each qualified environment with isolated HOME/XDG state and no provider
request. Measure:

- wall-clock startup/help latency;
- peak resident memory;
- child process count;
- imported module count;
- filesystem writes;
- network attempts;
- graceful behavior when optional capabilities are absent.

This phase must never launch an unqualified environment on the operator's live
configuration.

## Phase 3: capability tasks

Use the same model and prompt where possible. The initial task set should cover:

1. inspect a repository without mutation;
2. make and test a bounded code change;
3. hand a URL to the platform browser;
4. inspect an Android capability without acting;
5. recover and resume after an interrupted task.

Measure task success and correctness before cost. A cheaper failure is still a
failure wearing a tiny hat.

## Phase 4: token and request amplification

Instrument the provider transport for:

- request count per visible turn;
- input/output/cache token usage;
- repeated context bytes;
- tool-result continuation amplification;
- retry amplification;
- time to first token and total latency.

Do not compare different models as an architecture benchmark. If models differ,
report the result as an end-to-end product comparison instead.

## Phase 5: authority and recovery

Exercise bounded negative cases:

- missing or modified baseline manifest;
- modified plugin implementation;
- unavailable optional browser capability;
- interrupted overlay installation;
- stale or corrupted configuration;
- attempted engine repair under a reuse-only baseline;
- rollback without resolving packages from the network.

Security claims require threat modeling and adversarial tests. Package count is
an attack-surface signal, not proof of safety.

## Reporting rules

Every report must state:

- exact target identity and input hashes;
- device, OS, architecture, and interpreter;
- whether network/provider access occurred;
- whether the live operator environment was touched;
- which claims are directly measured;
- which claims remain hypotheses;
- failures and excluded targets.

The objective is not to manufacture a winning score. It is to identify where
platform substitution produces a measurable advantage and where framework
expansion earns its additional cost.
