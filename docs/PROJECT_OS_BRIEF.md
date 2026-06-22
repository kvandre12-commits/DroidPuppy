# Project OS Brief

## One-line idea

**Project OS** is the working doctrine that a modern project can run as an
operator-facing system across repos, agents, contracts, tools, and device
surfaces — not just as a pile of source files inside one laptop IDE.

## Why this matters here

Code Puppy gives us the engine.

DroidPuppy gives that engine **phone-native hands** on Android:

- apps
- intents
- settings surfaces
- browser handoff
- wireless ADB
- CDP browser control
- screenshots, UI hierarchy, input, logs, and support bundles

That turns a phone into part of the operator environment, not just a bad
terminal.

## The stack

```text
Project OS doctrine
    -> Code Puppy engine
        -> DroidPuppy Android overlay
            -> Android device surfaces
                -> real operator workflows
```

## What Project OS means in practice

### 0. Same-day install path stays upstream-first

Project OS should not require mutating Mike's repo or carrying a permanent fork
for the Android product layer.

The clean path is:

1. install upstream Code Puppy
2. clone DroidPuppy
3. run the light installer (`python scripts/install_overlay.py`)
4. let Code Puppy's plugin tiers load the Android-native overlay

That keeps the engine lean, keeps ownership clean, and makes the phone-native
layer portable.

### 1. Repo boundaries stay real

- Code Puppy owns the general engine.
- DroidPuppy owns Android orchestration.
- Domain systems (for example SharpEdge) own their own truth.

This is not one blob repo pretending to be architecture.

### 2. Contracts matter

Work should move through typed artifacts and observable handoffs, not vibes.

Examples in this repo:

- workflow captures
- support bundles
- Orchestra contracts
- task/observation/result boundaries
- eyes inbox artifacts and routed local queue items for human-surfaced evidence

### 3. The phone is a first-class surface

Project OS rejects the assumption that all serious operator computing has to
happen in a desktop IDE.

On Android, the real control plane includes:

- app launch and activity routing
- share sheets and intents
- browser sessions
- wireless debugging
- UI dump and input
- screenshots and logs

### 4. Safety is part of the platform

A real operator system must distinguish between:

- harmless reads
- idempotent actions
- irreversible side effects

That is why the Orchestra work and approval-gated execution matter.

## What Mike should see

The important message is not just "I built Android plugins."

It is:

> I used Code Puppy's engine as the base of a broader Project OS direction,
> where Android becomes a serious operator surface and the extension layer stays
> disciplined, testable, documented, and reviewable.

## Why DroidPuppy is the right demonstration

DroidPuppy is a good Project OS proof because it shows all the hard parts at
once:

- environment-specific seams
- plugin discipline instead of core sprawl
- observable tooling
- workflow thinking instead of toy commands
- safety boundaries around side effects
- real operator value on a constrained device

## Short takeaway

Project OS is the larger frame.

Code Puppy is the engine.

DroidPuppy is the Android-native operating layer that proves the engine can
leave the desktop and still behave like a serious system.
