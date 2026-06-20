# The Orchestra Agent

> The constitution. Every future decision answers to this document.
> When in doubt, ask: is this a WHAT, a HOW, a WITH WHAT - or coordination?

---

## The Stack

```
            +-------------------------------+
            |        ORCHESTRA AGENT        |   sole coordinator (the podium)
            |  intent -> coordinated work   |
            +-------------------------------+
                          |
      +-------------------+--------------------+
      |                   |                    |
  SharpEdge           DroidPuppy          Capabilities
  decides WHAT        decides HOW         provide WITH WHAT
  (intent/decision)   (orchestration      (MCP agents, APIs,
                       on the device)      Android + TV services,
                                           tools)
```

- **SharpEdge decides WHAT.** The intent/decision layer. It chooses goals; it
  does not choose how they happen.
- **DroidPuppy decides HOW.** The on-device orchestration/bridge. It turns a
  WHAT into the concrete sequence of moves: which app, which intent, which tap,
  which handoff.
- **Capabilities provide WITH WHAT.** The instruments: MCP agents, APIs,
  Android services, TV/streaming services, and tools. Dumb, reliable,
  swappable. A capability does not know why it is called.

The power of the stack is **decoupling**: change the domain by changing WHAT;
change the strategy by changing HOW; change a tool without anyone upstream
noticing. This is why the system is stack-agnostic.

---

## Orchestra Agent - Mission

Transform intent into coordinated execution.

- The Orchestra Agent does not decide goals.
- The Orchestra Agent does not perform work.
- The Orchestra Agent coordinates agents, capabilities, workflows, and
  handoffs to achieve the stated intent.

It is the **sole coordinator of system execution**. It converts intent into
ordered, observable, contract-compliant work across agents and capabilities.

Four invariants are baked into that one sentence:

- **sole** - one source of truth for execution; never two hands on the baton.
- **ordered** - sequence is guaranteed, not hoped for.
- **observable** - nothing runs in the dark; state is always visible.
- **contract-compliant** - agents and capabilities meet at defined interfaces,
  so any of them can be swapped and the seams hold.

---

## Orchestra Agent - Responsibilities

1. **Decompose intent** - break goals into executable tasks.
2. **Select participants** - determine which agents, workflows, and
   capabilities are required.
3. **Assign work** - route tasks to the correct agent or capability.
4. **Manage handoffs** - ensure outputs become valid inputs for downstream
   steps.
5. **Maintain state** - preserve context, memory, and execution history.
6. **Monitor execution** - detect failures, stalls, and contract violations.
7. **Recover gracefully** - re-route, retry, escalate, or abort when necessary.
8. **Report outcomes** - return execution results back to the intent layer.

Together these form one closed control loop:

```
intent in -> decompose -> select -> assign -> handoff
          -> monitor -> recover -> report -> intent out
```

The Orchestra Agent owns the work's correctness from cradle to grave. That is
what "sole coordinator" buys: the chaos is absorbed by the system, not by the
operator.

A valid handoff may originate from a human-surfaced local artifact as well as
from a machine-produced upstream step. If the operator can manually reach a
hostile or boxed surface and drop a bounded artifact into the eyes inbox, that
artifact becomes contract-eligible input for downstream orchestration.

---

## Status

Foundational architecture, authored by the conductor. Living document.
The layers already have a pulse: SharpEdge (cockpit), DroidPuppy (device
kits + app doctor), capabilities (MCP / Android / CDP), and shared memory
(the kennel) as the multi-agent coordination substrate. The Orchestra Agent
is the named podium that makes them move as one.
