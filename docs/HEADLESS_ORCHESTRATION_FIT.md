# Headless Orchestration Fit

## Why this note exists

The system already has a growing Project OS / Orchestra trail.
This note exists to prevent rebuilding the same idea under new labels when the
real job is to fit new execution tactics into the existing doctrine.

## The proposed model

The user's headless-orchestration framing is:

1. **Choreographer vs. Dancers**
   - heavy LLM parses intent and emits strict payloads
   - lightweight native scripts do the actual work and exit quickly
2. **Persistent local state**
   - SQLite or JSON so Android kills do not destroy progress
3. **Event-driven triggers**
   - wake on system/file/job events instead of running forever loops

## How it maps to the existing stack

### 1. Choreographer = already implied by Orchestra doctrine

This is not a new architectural religion.
It maps cleanly to the existing stack:

```text
SharpEdge / intent layer     -> decides WHAT
Orchestra / DroidPuppy layer -> decides HOW
Capabilities / scripts       -> provide WITH WHAT
```

That is already a separation-of-concerns model.

The practical interpretation should be:

- the **heavy LLM** runs in the foreground or on explicit wakeup
- it converts messy intent into bounded contract-compliant artifacts
- the **micro-workers** consume those artifacts and perform native work
- the heavy planner then gets out of the way

### 2. Strict JSON payloads = already aligned with contract doctrine

We already have contract-first thinking in this repo:

- Orchestra contracts under `contracts/v1/`
- eyes inbox artifacts and queue items as supplemental intake contracts
- documented handoff discipline: no validation, no handoff

So the right move is **not** to invent a parallel ad-hoc command protocol.
It is to keep using typed JSON artifacts as the seam between planning and
execution.

### 3. Dancers = bounded scripts/adapters, not mini-chaos agents

The lightweight workers should live in the execution layer as:

- narrow Python/Bash/JS scripts
- adapter-like runners
- one input artifact in
- one output artifact/result out
- fast exit
- no long hidden scratchpad
- no dependency on an always-live foreground LLM session

That fits both the Orchestra idea and Android reality.

### 4. Persistent state = already present in two forms

This also fits existing prior art instead of requiring a reboot:

- `orchestra/kernel.py` already demonstrates a SQLite-backed durable substrate
  for intents/tasks/observations/results
- the eyes inbox slice already uses durable JSON artifacts and queue items under
  `~/.project_os/eyes/`

So the real decision is not **whether** to persist state.
It is **which persistence mode belongs to which worker class**:

- SQLite for richer resumable orchestration state
- JSON files for cheap local handoff queues and manifests

### 5. Event-driven triggers = matches the Project OS runtime direction

The kennel trail already established:

- Event Record before Event Queue
- Event Queue before Scheduler
- Scheduler before Agent Lease allocation
- scheduler is not sovereign

That means wakeups should be event-driven and bounded.

For Android/Termux, this points toward things like:

- file-drop triggers
- `termux-job-scheduler`
- operator-invoked one-shot runs
- explicit share/handoff actions

and **away from**:

- permanent `while True` daemons
- constant polling loops
- heavyweight always-on agents pretending Android is a server rack

## Implementation stance

We should **not** pause to write a whole new scenario-only architecture pass.
That modeling work mostly already exists across:

- Orchestra doctrine
- Project OS scheduler/runtime trail
- eyes inbox contracts and intake lane
- Android ingress plugin work

We also should **not** jump straight to a giant autonomous runtime.
That would recreate work badly and fight Android.

The correct stance is:

```text
existing doctrine stays
existing contracts stay
existing durable state patterns stay
implement the next thin event-driven worker slice directly
```

## What this means right now

The next useful slice should look like:

1. **foreground choreographer**
   - optional heavy planning step
   - emits bounded JSON work item(s)
2. **eyes inbox / queue**
   - durable handoff seam
3. **one-shot worker**
   - reads one pending queue item
   - performs one bounded transformation
   - writes result/observation
   - exits
4. **event wakeup**
   - manual trigger, file trigger, or Termux scheduler trigger
5. **review/report path**
   - notification, queue status, or operator brief

This repo now has the first direct implementation of that shape in the eyes
lane:

- `scripts/eyes_queue_worker.py` = one-shot worker
- `scripts/eyes_review_gate.py` = minimal review artifact + notification gate + approve/reject CLI
- `scripts/eyes_tick.py` = one-shot scan + consume scheduler target
- `android_eyes_worker_kit` = Android/agent-facing wrapper around run/schedule/list/cancel

## Android-native execution rules

The remaining discipline is not conceptual. It is operational.

Android is not a polite little server. It will kill background work, squeeze RAM,
and hide failures unless the runtime behaves like a mobile system on purpose.

### Foreground owns the human gateway

The following belongs in the foreground or in an explicit operator session:

- CLI / chat / terminal control
- initial environment checks and doctor flows
- permission and setup gates
- high-context heavy-planning turns
- explicit approval / rejection decisions

The heavy planner should be short-lived and wake on demand. Do not pretend a
full-fat LLM session deserves to squat in RAM forever.

### Background owns bounded work

The following can detach into event-driven one-shot work:

- queue consumption
- local indexing / embeddings
- passive telemetry collection
- cleanup / maintenance tasks
- deterministic artifact transforms

The Android-safe rule is:

```text
short-lived worker in
-> one bounded artifact consumed
-> one typed result / observation written
-> worker exits
```

That is safer than a fake immortal loop that lives exactly until Android gets
bored and strangles it.

### Persistence posture beats optimism

Long-lived behavior on Android should assume at least one of these is needed:

- `termux-job-scheduler` style wakeups
- explicit battery-optimization exemptions
- foreground-service style persistence where a native Android wrapper exists
- frequent checkpoint writes to local storage

Do not treat a background shell surviving yesterday as architecture.
That is just a lucky anecdote wearing a fake beard.

## Review boundary vs auto-run boundary

### Human review should gate

- destructive shell commands
- non-sandbox file mutation
- package installation or environment mutation
- edits to core prompts / behavioral rules
- high-effect Android intents or browser actions outside approved lease scope
- loops that exceed iteration, retry, or token-budget thresholds

### Auto-run is fine for

- passive device-state reads
- queue ingestion
- deterministic low-risk maintenance
- support telemetry and health checks
- artifact validation and routing

This matches the existing governance trail:

```text
Review Required -> Operator Decision -> Audit Event -> Lease -> later bounded effect
```

## Success, failure, and reconciliation

Success should not mean "the model sounded confident." It should mean:

- the selected tool actually executed
- the tool returned schema-valid structured data
- the result artifact was written durably
- the system reconciled that the intended state change happened

Failure on Android includes boring ugly things, not just thrown exceptions:

- LMK / OOM process death mid-turn
- context overrun without graceful truncation
- malformed tool-call payloads or hallucinated tools
- silent partial execution with no durable result artifact

The runtime therefore needs a dedicated execution journal or equivalent durable
trace. If a process dies mid-step, the next wakeup should be able to answer:

- what queue item was active
- which step started
- whether the effect fired
- whether a result artifact was written
- whether a human review is now required

## Memory model on Android

Short-term state should be serialized aggressively:

- current task / queue item
- intermediate step outputs
- retry counters
- active constraints / lease context
- last successful checkpoint

Long-term state should persist as stable local knowledge:

- tool schemas and capability routes
- known-good device limits and RAM/context ceilings
- user preferences and approved operating habits
- durable failure signatures and recovery hints

SQLite and JSON both already exist in the doctrine. Use the cheap substrate that
fits the worker class; do not build an unnecessary state cathedral for a one-shot
script.

## Observability rule

On Android, terminal visibility is not trustworthy enough to count as
observability.

The runtime must continuously flush execution state to local durable storage so a
reboot or kill can reconcile the exact failure edge. In practice that means:

- append-only or checkpointed local run logs
- typed result / review / audit artifacts
- resumable queue state
- operator-visible status on next wakeup

If the only record of progress lived in scrollback, then the system did not
really observe itself. It just had thoughts near a terminal.

## Short answer

The proposal fits the long-term kennels very well.

It should be treated as:

- **an execution refinement of Orchestra / Project OS**, not a competing design
- **a direct thin-slice implementation target now**, not a reason to start the doctrine over

In plain English:

> keep the choreographer smart and short-lived,
> keep the dancers dumb and fast,
> keep state on disk,
> let events wake work up,
> and stop making Android fight us for sport.

The governance refinement now demonstrated in the eyes lane is:

```text
Review Required -> Operator Decision -> Audit Event -> Lease -> later harmless action
```
