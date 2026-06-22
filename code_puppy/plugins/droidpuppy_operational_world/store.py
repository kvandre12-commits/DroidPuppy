"""Durable storage primitives for the DroidPuppy operational world.

The store is intentionally boring: JSON state + append-only JSONL stream. Boring
survives Android kills. Fancy survives demos. We like boring.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_SPEC = "droidpuppy.world_spec.v1"
SCHEMA_STATE = "droidpuppy.world_state.v1"
SCHEMA_EVENT = "droidpuppy.world_event.v1"
DEFAULT_WORLD_ROOT = Path.home() / ".project_os" / "droidpuppy_world"


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def event_id(prefix: str = "evt") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def resolve_root(root: str = "") -> Path:
    return Path(root).expanduser().resolve() if root.strip() else DEFAULT_WORLD_ROOT


def paths(root: str = "") -> dict[str, Path]:
    base = resolve_root(root)
    return {
        "root": base,
        "spec": base / "world_spec.json",
        "state": base / "world_state.json",
        "stream": base / "stream.jsonl",
    }


def ensure_layout(root: str = "") -> dict[str, Path]:
    resolved = paths(root)
    resolved["root"].mkdir(parents=True, exist_ok=True)
    return resolved


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(default or {})
    return payload if isinstance(payload, dict) else dict(default or {})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    tmp.replace(path)


def append_event(
    root: str, event_type: str, payload: dict[str, Any], *, source: str
) -> dict[str, Any]:
    resolved = ensure_layout(root)
    event = {
        "schema_version": SCHEMA_EVENT,
        "event_id": event_id(),
        "timestamp": utc_now(),
        "event_type": event_type,
        "source": source,
        "payload": payload,
    }
    with resolved["stream"].open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")
    return event


def read_stream(root: str = "") -> list[dict[str, Any]]:
    stream_path = paths(root)["stream"]
    if not stream_path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in stream_path.read_text(encoding="utf-8").splitlines():
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
    return events


def read_stream_tail(root: str = "", limit: int = 20) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    return read_stream(root)[-limit:]


def load_spec(root: str = "") -> dict[str, Any]:
    return read_json(paths(root)["spec"], default_spec())


def save_spec(root: str, spec: dict[str, Any]) -> None:
    write_json(paths(root)["spec"], spec)


def load_state(root: str = "") -> dict[str, Any]:
    return read_json(paths(root)["state"], default_state())


def save_state(root: str, state: dict[str, Any]) -> None:
    write_json(paths(root)["state"], state)


def default_spec() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_SPEC,
        "world_id": "droidpuppy-operational-world",
        "description": "Android-side operational world: tools/apps/tasks as auditable entities.",
        "entities": [
            {
                "id": "device",
                "type": "android_device",
                "properties": {"status": "unknown"},
            },
            {"id": "operator", "type": "human", "properties": {"role": "owner"}},
            {
                "id": "sharpedge",
                "type": "agent",
                "properties": {"role": "orchestrator"},
            },
        ],
        "actions": {
            "note": {
                "description": "Record a durable operator/world note.",
                "risk_tier": "read_only",
                "effects": [{"op": "emit_event", "event_type": "world.note"}],
            },
            "mark_entity": {
                "description": "Set one top-level property on an entity.",
                "risk_tier": "state_write",
                "effects": [{"op": "set_property"}],
            },
            "shell.exec": {
                "description": "Represent a shell command request; execution is out-of-band.",
                "risk_tier": "destructive",
                "requires_approval": True,
                "effects": [
                    {"op": "emit_event", "event_type": "shell.exec.approved_request"}
                ],
            },
        },
        "perception": {
            "operator": {
                "entity_types": ["*"],
                "event_types": ["*"],
                "hidden_properties": [],
            },
            "worker": {
                "entity_types": ["task", "android_device", "approval", "agent"],
                "event_types": ["action.*", "world.*", "consequence.*", "approval.*"],
                "hidden_properties": ["secret", "token", "credential"],
            },
            "audit": {
                "entity_types": ["*"],
                "event_types": ["*"],
                "hidden_properties": [],
            },
        },
        "consequences": [
            {
                "id": "approval-gate-visible",
                "when": {"event_type": "approval.required"},
                "emit": {
                    "event_type": "consequence.approval_gate",
                    "payload": {
                        "message": "Approval required before this action can advance."
                    },
                },
            }
        ],
    }


def default_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_STATE,
        "world_id": "droidpuppy-operational-world",
        "tick": 0,
        "updated_at": utc_now(),
        "entities": {},
        "queued_actions": [],
        "processed_action_ids": [],
        "fired_consequence_keys": [],
    }
