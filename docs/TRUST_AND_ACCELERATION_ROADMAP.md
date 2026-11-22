# Trust and Acceleration Roadmap

## Goal

The operator's goal is to make DroidPuppy difficult to silently corrupt. Literal
"uncorruptable" software does not exist. The engineering target is:

- deny-by-default authority;
- hardware-rooted identity;
- tamper-evident code and receipts;
- bounded effects outside the model process;
- reproducible recovery;
- explicit, independently replaceable acceleration lanes.

Compromise must become difficult, visible, bounded, and recoverable.

## Read-only posture audit

Run the stdlib-only audit without changing configuration:

```bash
python scripts/audit_platform_trust.py
```

It checks boot/encryption properties, hardware trust features, the global MCP
default, native compute libraries/features, and whether the installed llama.cpp
reports an accelerator. It reads no credential values and makes no root or
invulnerability claim.

## Verified platform direction

The current target device is Android/ARM64 on a Qualcomm SM8750-class platform.
The platform exposes Adreno OpenCL libraries, Vulkan compute, hardware Keystore,
StrongBox, and app-attestation features. It does not expose NVIDIA CUDA.

The installed `llama.cpp` binaries are Android/aarch64 builds, but
`llama-cli --list-devices` currently reports no accelerator devices. Local
inference is therefore CPU-only even though the platform provides GPU compute
primitives.

The correct substitution is:

```text
not: phone -> imitate NVIDIA workstation -> CUDA

but: phone -> qualify native Adreno compute -> Vulkan/OpenCL backend
```

CUDA remains appropriate on qualified NVIDIA hosts. It is not a portable name
for all GPU acceleration.

## Trust architecture

### 1. Immutable recovery root

Keep protected baselines append-only by identity. Never silently edit
`june-brave-v1`; create a successor ID. Preserve manifests, implementation tree
hashes, tests, receipts, and rollback instructions outside the mutable runtime.

### 2. Hardware-backed signing

The existing Android-native receipt helper truthfully reports that Python HMAC
is not hardware-backed. Build a minimal native Android companion that:

- creates a non-exportable StrongBox/KeyMint signing key;
- signs canonical baseline and execution receipt hashes;
- returns signatures and certificate/attestation metadata;
- never gives private key material to Python or the model process.

A hardware signature proves key possession and measured receipt content. It
does not prove the signed code was benign.

### 3. External execution broker

In-process callbacks are cooperative policy, not a security boundary. Move
mutating effects behind a separate, small broker with:

- a deny-by-default capability allowlist;
- typed, bounded requests;
- path/package/URL scopes;
- short-lived approvals;
- no general shell primitive for ordinary effects;
- readback and rollback where possible;
- a receipt for every accepted or denied request.

The model proposes. The broker decides and executes. The broker must remain
useful with the model process fully compromised.

### 4. Default-off extension surfaces

Protected profiles should default to:

- MCP disabled globally;
- no project plugin trust inherited across repositories;
- no unknown plugin imports;
- no automatic provider/sandbox installation;
- no browser attachment until explicitly requested;
- no speculative code mode in the trusted baseline;
- no write primitive below the capability tier that has earned it.

Enable one named capability for one bounded task rather than enabling an entire
integration catalog.

### 5. Secret separation

Do not expose durable credentials to the agent process when a broker can hold
them. Prefer:

- Android Keystore non-exportable keys;
- short-lived scoped tokens;
- provider-specific helper processes;
- redacted logs;
- explicit credential inventory and rotation receipts.

Hashing a secret is not the same as removing its authority.

### 6. Tamper-evident evidence

Use append-only, hash-chained records with periodic StrongBox-signed checkpoints.
Store enough metadata to reproduce authority and outcome without recording
prompts, credentials, or private user content by default.

Tamper evidence detects history changes. It does not prevent deletion, so copy
checkpoints to a second operator-controlled location.

### 7. Qualified updates

Separate:

```text
protected baseline  -> immutable recovery/control specimen
qualified successor -> security fixes proven on target devices
experimental lane   -> new frameworks and acceleration work
```

Never let an experimental lane overwrite the recovery root. Promotion requires
receipts from at least two real target devices, negative tests, and rollback.

## Acceleration lane

### T0: inventory

Record SoC, ABI, Vulkan/OpenCL availability, thermal state, current llama.cpp
build identity, and `--list-devices`. No rebuild and no model request.

### T1: isolated Vulkan/OpenCL build

Build a separate llama.cpp candidate with one native backend. Do not replace the
working CPU binary. Pin source SHA, compiler, flags, and output hashes.

### T2: deterministic correctness

Using the same model and fixed prompts, compare CPU and accelerator candidates:

- exact tokenization;
- output validity under deterministic settings;
- model-load success;
- crashes and driver errors;
- numerical divergence where observable.

### T3: performance and thermals

Measure:

- model-load time;
- prompt processing tokens/second;
- generation tokens/second;
- peak resident memory;
- sustained temperature and throttling;
- energy use where Android exposes reliable counters;
- recovery after process interruption.

A faster first minute that overheats and collapses is not a successful mobile
backend.

### T4: optional promotion

Only after correctness, stability, and rollback pass should the accelerated
binary become an optional named profile. CPU remains the recovery backend.

## Current observations requiring a decision

The live configuration currently has MCP globally enabled. The main Code Puppy
binding observed in the audit is limited to `puppy-status`, and planning is
bound to a read-only governance server, but other enabled registry entries exist.
Changing that configuration may disrupt deliberate integrations, so the audit
does not mutate it. The protected-profile recommendation is default-off with
explicit per-agent enablement.

The presence of an `su` executable alone does not prove the Android device is
rooted; the audit intentionally makes no such claim. Verified boot, bootloader,
and encryption properties are stronger measured signals, but none prove the
entire userspace is uncompromised.

## One-line doctrine

> Root trust in hardware, keep effects outside the model, make every authority
> bounded and receipted, and preserve a recovery path that experiments cannot
> overwrite.
