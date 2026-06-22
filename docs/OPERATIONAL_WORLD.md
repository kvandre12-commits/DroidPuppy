# DroidPuppy Operational World

DroidPuppy is not just a CLI wrapper. It is an Android-side operational world:
stateful, tick-driven, auditable, and deterministic first.

## Contract

The first slice lives in the builtin overlay plugin:

```text
code_puppy/plugins/droidpuppy_operational_world/
```

It writes three durable files under `~/.project_os/droidpuppy_world/` by default.
The contract schemas live in:

- `contracts/v1/droidpuppy_world_spec.schema.json`
- `contracts/v1/droidpuppy_world_state.schema.json`
- `contracts/v1/droidpuppy_world_event.schema.json`

| File | Purpose |
| --- | --- |
| `world_spec.json` | Declarative world/workflow spec: entities, actions, perception rules, consequences. |
| `world_state.json` | Current tick, entities, queued actions, fired consequence keys. |
| `stream.jsonl` | Append-only replayable event stream. This is the audit spine. |

## Tool surface

| Tool | Purpose |
| --- | --- |
| `droidpuppy_world_doctor` | Inspect readiness, paths, current counts, and capabilities. |
| `droidpuppy_world_init` | Materialize state/spec from a JSON spec. |
| `droidpuppy_world_submit_action` | Queue an action. Nothing executes immediately. |
| `droidpuppy_world_tick` | Advance one deterministic tick and process queued actions. |
| `droidpuppy_world_perceive` | Return filtered state/events for a viewer (`operator`, `worker`, `audit`). |
| `droidpuppy_world_scan_consequences` | Run consequence rules against state/recent events. |
| `droidpuppy_world_reconcile_android` | Convert Android capability facts into durable device/command/lane entities. |
| `droidpuppy_world_replay` | Rebuild/summarize state facts from append-only `stream.jsonl`. |
| `droidpuppy_world_examples` | Show common calls. |

## Philosophy

The world loop is deliberately boring:

```text
submit action -> append action.queued -> tick -> validate policy -> apply deterministic effects -> scan consequences -> append events -> save state
```

Rules first. AI/human referee second.

Examples:

- `shell.exec` is represented as an action request, but **not executed** by this plugin.
- Dangerous actions can emit `approval.required` and create an approval entity.
- Consequence rules can turn that into `consequence.approval_gate`.
- Worker agents see only their perception-filtered slice, not the whole kitchen.

## Default action types

| Action | Behavior |
| --- | --- |
| `note` | Emits a durable `world.note` event. |
| `mark_entity` | Sets one top-level property on a target entity. |
| `shell.exec` | Requires approval; emits an approval entity/event instead of executing shell. |

## Spec shape

Minimal custom spec:

```json
{
  "schema_version": "droidpuppy.world_spec.v1",
  "world_id": "my-world",
  "entities": [
    {"id": "device", "type": "android_device", "properties": {"status": "unknown"}}
  ],
  "actions": {
    "note": {
      "risk_tier": "read_only",
      "effects": [{"op": "emit_event", "event_type": "world.note"}]
    }
  },
  "perception": {
    "operator": {"entity_types": ["*"], "event_types": ["*"], "hidden_properties": []}
  },
  "consequences": []
}
```

Supported deterministic effects in v1:

- `emit_event`
- `set_property`
- `create_entity`

Supported consequence matchers in v1:

- `{"event_type": "approval.required"}`
- `{"entity_property_equals": {"type": "task", "property": "status", "value": "stale"}}`

## Next build targets

1. Broader reconciliation: refresh app/browser/process entities from real tools.
2. Approval receipt integration: consume `droidpuppy_android_approval_receipt` envelopes.
3. Worker scheduler: run one bounded world tick through Termux job scheduler.
4. Android reconciliation entities: convert app/browser/device probes into world entities.
5. Referee lane: route ambiguous outcomes to human/AI without breaking deterministic audit.
