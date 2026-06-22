"""Tooling facade for DroidPuppy's operational world.

This is the first slice of "operational world, not XI/CLI wrapper": state is
durable, actions are queued, ticks reconcile, consequences fire, and perception
is filtered per actor. No shell execution happens here. Determinism first,
referee later. Tiny machine, sharp teeth.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .engine import (
    bootstrap_state_from_spec,
    perceive,
    process_tick,
    scan_consequences,
    submit_action,
)
from .reconcile import reconcile_android_world
from .store import (
    append_event,
    default_spec,
    ensure_layout,
    load_spec,
    load_state,
    paths,
    read_stream,
    read_stream_tail,
    save_spec,
    save_state,
    utc_now,
)


def _parse_json_object(text: str, *, field: str) -> tuple[dict[str, Any] | None, str]:
    if not text.strip():
        return {}, ""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"{field} is not valid JSON: {exc}"
    if not isinstance(parsed, dict):
        return None, f"{field} must decode to a JSON object"
    return parsed, ""


def _load_spec_from_arg(
    spec_json: str = "", spec_path: str = ""
) -> tuple[dict[str, Any] | None, str]:
    if spec_json.strip():
        return _parse_json_object(spec_json, field="spec_json")
    if spec_path.strip():
        path = Path(spec_path).expanduser()
        if not path.is_file():
            return None, f"spec_path does not exist: {path}"
        return _parse_json_object(path.read_text(encoding="utf-8"), field="spec_path")
    return default_spec(), ""


def droidpuppy_world_doctor(root: str = "") -> dict[str, Any]:
    """Inspect operational world readiness and current durable files."""
    resolved = paths(root)
    state = load_state(root)
    spec = load_spec(root)
    return {
        "success": True,
        "root": str(resolved["root"]),
        "files": {key: str(path) for key, path in resolved.items() if key != "root"},
        "exists": {
            key: path.exists() for key, path in resolved.items() if key != "root"
        },
        "world_id": state.get("world_id") or spec.get("world_id"),
        "tick": state.get("tick", 0),
        "entity_count": len(state.get("entities") or {}),
        "queued_action_count": len(state.get("queued_actions") or []),
        "stream_tail_count": len(read_stream_tail(root, limit=5)),
        "capabilities": {
            "declarative_spec": True,
            "tick_driven_orchestration": True,
            "per_agent_perception": True,
            "append_only_event_stream": True,
            "consequence_scanner": True,
            "deterministic_rules_first": True,
            "ai_referee": False,
        },
        "guidance": [
            "Run droidpuppy_world_init once to materialize spec/state.",
            "Queue work with droidpuppy_world_submit_action; no action executes until tick.",
            "Run droidpuppy_world_tick to advance deterministic state.",
            "Use droidpuppy_world_perceive(viewer='worker') for filtered agent context.",
        ],
    }


def droidpuppy_world_init(
    root: str = "",
    spec_json: str = "",
    spec_path: str = "",
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create or refresh an operational world from a declarative JSON spec."""
    resolved = ensure_layout(root)
    spec, error = _load_spec_from_arg(spec_json=spec_json, spec_path=spec_path)
    if error or spec is None:
        return {"success": False, "reason": error}
    if resolved["spec"].exists() and not overwrite:
        spec = load_spec(root)
    else:
        save_spec(root, spec)

    state = load_state(root)
    if not resolved["state"].exists() or overwrite:
        state = {
            **state,
            "world_id": spec.get(
                "world_id", state.get("world_id", "droidpuppy-operational-world")
            ),
            "tick": 0 if overwrite else state.get("tick", 0),
            "updated_at": utc_now(),
            "entities": {} if overwrite else state.get("entities", {}),
            "queued_actions": [] if overwrite else state.get("queued_actions", []),
            "processed_action_ids": []
            if overwrite
            else state.get("processed_action_ids", []),
            "fired_consequence_keys": []
            if overwrite
            else state.get("fired_consequence_keys", []),
        }
    state = bootstrap_state_from_spec(state, spec)
    save_state(root, state)
    event = append_event(
        root,
        "world.initialized",
        {"world_id": state.get("world_id"), "overwrite": overwrite},
        source="droidpuppy.operational_world",
    )
    return {
        "success": True,
        "root": str(resolved["root"]),
        "spec_path": str(resolved["spec"]),
        "state_path": str(resolved["state"]),
        "stream_path": str(resolved["stream"]),
        "event": event,
        "state": {
            "tick": state.get("tick"),
            "entity_count": len(state.get("entities") or {}),
        },
    }


def droidpuppy_world_submit_action(
    action_type: str,
    actor: str = "operator",
    target: str = "",
    payload_json: str = "{}",
    root: str = "",
) -> dict[str, Any]:
    """Queue an action into the operational world; ticks process it later."""
    if not action_type.strip():
        return {"success": False, "reason": "action_type is required"}
    payload, error = _parse_json_object(payload_json, field="payload_json")
    if error or payload is None:
        return {"success": False, "reason": error}
    spec = load_spec(root)
    state = bootstrap_state_from_spec(load_state(root), spec)
    state, action = submit_action(
        state,
        actor=actor,
        action_type=action_type,
        target=target,
        payload=payload,
    )
    save_state(root, state)
    event = append_event(
        root,
        "action.queued",
        {"action": action},
        source="droidpuppy.operational_world",
    )
    return {
        "success": True,
        "action": action,
        "event": event,
        "queued_action_count": len(state.get("queued_actions") or []),
    }


def droidpuppy_world_tick(
    root: str = "", max_actions: int = 10, dry_run: bool = False
) -> dict[str, Any]:
    """Advance the world one tick and process queued deterministic actions."""
    spec = load_spec(root)
    state = bootstrap_state_from_spec(load_state(root), spec)
    next_state, events = process_tick(
        root,
        spec,
        state,
        max_actions=max_actions,
        dry_run=dry_run,
    )
    if not dry_run:
        save_state(root, next_state)
    return {
        "success": True,
        "dry_run": dry_run,
        "tick": next_state.get("tick"),
        "events": events,
        "event_types": [event.get("event_type") for event in events],
        "queued_action_count": len(next_state.get("queued_actions") or []),
        "entity_count": len(next_state.get("entities") or {}),
        "state_written": not dry_run,
    }


def droidpuppy_world_perceive(
    viewer: str = "operator",
    root: str = "",
    stream_tail: int = 20,
) -> dict[str, Any]:
    """Return a viewer-filtered operational-world perception packet."""
    spec = load_spec(root)
    state = bootstrap_state_from_spec(load_state(root), spec)
    view = perceive(
        spec,
        state,
        read_stream_tail(root, limit=stream_tail),
        viewer=viewer,
    )
    return {"success": True, "perception": view}


def droidpuppy_world_scan_consequences(
    root: str = "", dry_run: bool = False
) -> dict[str, Any]:
    """Run consequence scanner against durable state and recent event tail."""
    spec = load_spec(root)
    state = bootstrap_state_from_spec(load_state(root), spec)
    events = scan_consequences(
        root,
        spec,
        state,
        read_stream_tail(root, limit=50),
        dry_run=dry_run,
    )
    if not dry_run:
        save_state(root, state)
    return {
        "success": True,
        "dry_run": dry_run,
        "events": events,
        "event_types": [event.get("event_type") for event in events],
        "state_written": not dry_run,
    }


def droidpuppy_world_reconcile_android(
    root: str = "",
    capabilities_json: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Reconcile Android capability facts into operational-world entities."""
    return reconcile_android_world(
        root=root,
        capabilities_json=capabilities_json,
        dry_run=dry_run,
    )


def droidpuppy_world_replay(
    root: str = "", write_state: bool = False
) -> dict[str, Any]:
    """Replay stream.jsonl into a reconstructed state summary."""
    spec = load_spec(root)
    state = bootstrap_state_from_spec(
        {
            "schema_version": "droidpuppy.world_state.v1",
            "world_id": spec.get("world_id", "droidpuppy-operational-world"),
            "tick": 0,
            "updated_at": utc_now(),
            "entities": {},
            "queued_actions": [],
            "processed_action_ids": [],
            "fired_consequence_keys": [],
        },
        spec,
    )
    counts: dict[str, int] = {}
    unknown_event_types: set[str] = set()
    for event in read_stream(root):
        event_type = str(event.get("event_type") or "")
        counts[event_type] = counts.get(event_type, 0) + 1
        _replay_event(state, event, unknown_event_types)
    if write_state:
        save_state(root, state)
    return {
        "success": True,
        "write_state": write_state,
        "state_written": write_state,
        "event_counts": counts,
        "unknown_event_types": sorted(unknown_event_types),
        "replayed_state": {
            "world_id": state.get("world_id"),
            "tick": state.get("tick", 0),
            "entity_count": len(state.get("entities") or {}),
            "queued_action_count": len(state.get("queued_actions") or []),
            "processed_action_count": len(state.get("processed_action_ids") or []),
        },
    }


def _replay_event(
    state: dict[str, Any],
    event: dict[str, Any],
    unknown_event_types: set[str],
) -> None:
    event_type = str(event.get("event_type") or "")
    payload = dict(event.get("payload") or {})
    if event_type == "world.initialized":
        state["world_id"] = payload.get("world_id", state.get("world_id"))
    elif event_type == "action.queued":
        action = dict(payload.get("action") or {})
        if action.get("action_id"):
            state.setdefault("queued_actions", []).append(action)
    elif event_type in {"action.accepted", "action.rejected", "approval.required"}:
        action = dict(payload.get("action") or {})
        _mark_action_processed(state, action)
        if event_type == "approval.required" and action.get("action_id"):
            _replay_approval_entity(state, action, payload)
    elif event_type == "entity.property_set":
        entity_id = str(payload.get("entity_id") or "")
        prop = str(payload.get("property") or "")
        if entity_id and prop and entity_id in state.get("entities", {}):
            state["entities"][entity_id].setdefault("properties", {})[prop] = (
                payload.get("value")
            )
            state["entities"][entity_id]["updated_at"] = utc_now()
    elif event_type == "entity.created":
        entity = dict(payload.get("entity") or {})
        if entity.get("id"):
            state.setdefault("entities", {})[str(entity["id"])] = entity
    elif event_type == "world.tick.completed":
        state["tick"] = int(dict(payload).get("tick") or state.get("tick") or 0)
    elif event_type.startswith(("world.", "consequence.", "effect.", "shell.")):
        return
    else:
        unknown_event_types.add(event_type)


def _mark_action_processed(state: dict[str, Any], action: dict[str, Any]) -> None:
    action_id = action.get("action_id")
    if not action_id:
        return
    state["queued_actions"] = [
        item
        for item in state.get("queued_actions", [])
        if item.get("action_id") != action_id
    ]
    if action_id not in state.setdefault("processed_action_ids", []):
        state["processed_action_ids"].append(action_id)


def _replay_approval_entity(
    state: dict[str, Any],
    action: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    action_id = action["action_id"]
    entity_id = f"approval-{action_id}"
    state.setdefault("entities", {})[entity_id] = {
        "id": entity_id,
        "type": "approval",
        "properties": {
            "status": "pending",
            "action_id": action_id,
            "action_type": action.get("action_type"),
            "actor": action.get("actor"),
            "risk_tier": payload.get("risk_tier", "review_required"),
        },
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }


def droidpuppy_world_examples() -> dict[str, Any]:
    """Show tiny operational-world examples."""
    return {
        "success": True,
        "examples": [
            {
                "goal": "Initialize the default operational world",
                "call": "droidpuppy_world_init(overwrite=False)",
            },
            {
                "goal": "Queue a durable note",
                "call": "droidpuppy_world_submit_action(action_type='note', payload_json='{\"message\":\"battery okay\"}')",
            },
            {
                "goal": "Advance one deterministic tick",
                "call": "droidpuppy_world_tick(max_actions=10)",
            },
            {
                "goal": "Get filtered worker perception",
                "call": "droidpuppy_world_perceive(viewer='worker', stream_tail=10)",
            },
            {
                "goal": "Represent dangerous shell request without executing it",
                "call": "droidpuppy_world_submit_action(action_type='shell.exec', payload_json='{\"command\":\"rm -rf /tmp/nope\"}')",
            },
            {
                "goal": "Reconcile Android capabilities into world entities",
                "call": "droidpuppy_world_reconcile_android()",
            },
        ],
        "contract": {
            "executes_shell": False,
            "state_file": "world_state.json",
            "stream_file": "stream.jsonl",
            "spec_file": "world_spec.json",
        },
    }
