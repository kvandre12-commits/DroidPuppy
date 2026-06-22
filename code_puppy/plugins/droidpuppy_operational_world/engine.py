"""Deterministic engine for the DroidPuppy operational world."""

from __future__ import annotations

import copy
from typing import Any

from .store import append_event, event_id, utc_now

RISK_ORDER = {"read_only": 0, "state_write": 1, "external_write": 2, "destructive": 3}


def bootstrap_state_from_spec(
    state: dict[str, Any], spec: dict[str, Any]
) -> dict[str, Any]:
    """Ensure declarative entities exist in state without clobbering live values."""
    state = copy.deepcopy(state)
    entities = state.setdefault("entities", {})
    for item in spec.get("entities", []):
        if not isinstance(item, dict) or not item.get("id"):
            continue
        entity_id = str(item["id"])
        existing = entities.setdefault(
            entity_id,
            {
                "id": entity_id,
                "type": str(item.get("type") or "entity"),
                "properties": {},
                "created_at": utc_now(),
                "updated_at": utc_now(),
            },
        )
        existing.setdefault("type", str(item.get("type") or "entity"))
        existing.setdefault("properties", {})
        for key, value in dict(item.get("properties") or {}).items():
            existing["properties"].setdefault(key, value)
    state["updated_at"] = utc_now()
    return state


def submit_action(
    state: dict[str, Any],
    *,
    actor: str,
    action_type: str,
    target: str = "",
    payload: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Queue an action for the next tick."""
    payload = payload or {}
    state = copy.deepcopy(state)
    action = {
        "action_id": event_id("act"),
        "actor": actor.strip() or "operator",
        "action_type": action_type.strip(),
        "target": target.strip(),
        "payload": payload,
        "status": "queued",
        "created_at": utc_now(),
    }
    state.setdefault("queued_actions", []).append(action)
    state["updated_at"] = utc_now()
    return state, action


def process_tick(
    root: str,
    spec: dict[str, Any],
    state: dict[str, Any],
    *,
    max_actions: int = 10,
    dry_run: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Advance the operational world one deterministic tick."""
    next_state = copy.deepcopy(state)
    next_state["tick"] = int(next_state.get("tick") or 0) + 1
    next_state["updated_at"] = utc_now()
    queued = list(next_state.get("queued_actions") or [])
    to_process = queued[: max(0, max_actions)]
    remaining = queued[len(to_process) :]
    next_state["queued_actions"] = remaining

    emitted: list[dict[str, Any]] = []
    tick_event = _event(
        root,
        "world.tick.started",
        {"tick": next_state["tick"], "dry_run": dry_run},
        dry_run,
    )
    emitted.append(tick_event)

    for action in to_process:
        result_events = _process_action(root, spec, next_state, action, dry_run=dry_run)
        emitted.extend(result_events)
        next_state.setdefault("processed_action_ids", []).append(action["action_id"])

    emitted.extend(scan_consequences(root, spec, next_state, emitted, dry_run=dry_run))
    emitted.append(
        _event(root, "world.tick.completed", {"tick": next_state["tick"]}, dry_run)
    )
    return next_state, emitted


def scan_consequences(
    root: str,
    spec: dict[str, Any],
    state: dict[str, Any],
    recent_events: list[dict[str, Any]] | None = None,
    *,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """Evaluate declarative consequence rules against state + recent events."""
    recent_events = recent_events or []
    emitted: list[dict[str, Any]] = []
    fired = set(state.setdefault("fired_consequence_keys", []))
    for rule in spec.get("consequences", []):
        if not isinstance(rule, dict) or not rule.get("id"):
            continue
        matches = _matching_consequence_keys(rule, state, recent_events)
        for key in matches:
            if key in fired:
                continue
            fired.add(key)
            state["fired_consequence_keys"].append(key)
            emit_cfg = dict(rule.get("emit") or {})
            event_type = emit_cfg.get("event_type") or "consequence.triggered"
            payload = dict(emit_cfg.get("payload") or {})
            payload.update({"rule_id": rule["id"], "match_key": key})
            emitted.append(_event(root, str(event_type), payload, dry_run))
    return emitted


def perceive(
    spec: dict[str, Any],
    state: dict[str, Any],
    stream_tail: list[dict[str, Any]],
    *,
    viewer: str = "operator",
) -> dict[str, Any]:
    """Return a filtered view of state for an operator/agent/auditor."""
    rules = dict(
        spec.get("perception", {}).get(viewer)
        or spec.get("perception", {}).get("worker")
        or {}
    )
    entity_patterns = list(rules.get("entity_types") or [])
    event_patterns = list(rules.get("event_types") or [])
    hidden = set(rules.get("hidden_properties") or [])
    entities = {
        entity_id: _hide_properties(entity, hidden)
        for entity_id, entity in dict(state.get("entities") or {}).items()
        if _matches_any(str(entity.get("type") or "entity"), entity_patterns)
    }
    events = [
        event
        for event in stream_tail
        if _matches_any(str(event.get("event_type") or ""), event_patterns)
    ]
    return {
        "viewer": viewer,
        "world_id": state.get("world_id"),
        "tick": state.get("tick", 0),
        "entities": entities,
        "queued_action_count": len(state.get("queued_actions") or []),
        "events": events,
    }


def _process_action(
    root: str,
    spec: dict[str, Any],
    state: dict[str, Any],
    action: dict[str, Any],
    *,
    dry_run: bool,
) -> list[dict[str, Any]]:
    actions = dict(spec.get("actions") or {})
    cfg = actions.get(action.get("action_type"))
    if cfg is None:
        return [
            _event(
                root,
                "action.rejected",
                {"action": action, "reason": "unknown_action"},
                dry_run,
            )
        ]
    if _approval_required(cfg, action):
        _create_approval_entity(state, action, cfg)
        return [
            _event(
                root,
                "approval.required",
                {"action": action, "risk_tier": cfg.get("risk_tier")},
                dry_run,
            )
        ]
    emitted = [_event(root, "action.accepted", {"action": action}, dry_run)]
    for effect in list(cfg.get("effects") or []):
        emitted.extend(_apply_effect(root, state, action, effect, dry_run=dry_run))
    return emitted


def _approval_required(cfg: dict[str, Any], action: dict[str, Any]) -> bool:
    if not cfg.get("requires_approval"):
        return False
    payload = dict(action.get("payload") or {})
    return not bool(payload.get("approved") or payload.get("approval_receipt"))


def _create_approval_entity(
    state: dict[str, Any], action: dict[str, Any], cfg: dict[str, Any]
) -> None:
    entity_id = f"approval-{action['action_id']}"
    state.setdefault("entities", {})[entity_id] = {
        "id": entity_id,
        "type": "approval",
        "properties": {
            "status": "pending",
            "action_id": action["action_id"],
            "action_type": action.get("action_type"),
            "actor": action.get("actor"),
            "risk_tier": cfg.get("risk_tier", "review_required"),
        },
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }


def _apply_effect(
    root: str,
    state: dict[str, Any],
    action: dict[str, Any],
    effect: dict[str, Any],
    *,
    dry_run: bool,
) -> list[dict[str, Any]]:
    op = effect.get("op")
    if op == "set_property":
        return _effect_set_property(root, state, action, effect, dry_run=dry_run)
    if op == "create_entity":
        return _effect_create_entity(root, state, action, effect, dry_run=dry_run)
    if op == "emit_event":
        event_type = str(
            effect.get("event_type") or action.get("action_type") or "action.event"
        )
        payload = {"action": action, **dict(effect.get("payload") or {})}
        return [_event(root, event_type, payload, dry_run)]
    return [
        _event(
            root,
            "effect.skipped",
            {"action": action, "effect": effect, "reason": "unknown_effect"},
            dry_run,
        )
    ]


def _effect_set_property(
    root: str,
    state: dict[str, Any],
    action: dict[str, Any],
    effect: dict[str, Any],
    *,
    dry_run: bool,
) -> list[dict[str, Any]]:
    payload = dict(action.get("payload") or {})
    target = str(
        effect.get("entity") or action.get("target") or payload.get("entity") or ""
    )
    prop = str(effect.get("property") or payload.get("property") or "")
    value = effect.get("value", payload.get("value"))
    entity = dict(state.setdefault("entities", {}).get(target) or {})
    if not target or not prop or not entity:
        return [
            _event(
                root,
                "effect.failed",
                {"action": action, "reason": "missing_entity_or_property"},
                dry_run,
            )
        ]
    entity.setdefault("properties", {})[prop] = value
    entity["updated_at"] = utc_now()
    state["entities"][target] = entity
    return [
        _event(
            root,
            "entity.property_set",
            {
                "entity_id": target,
                "property": prop,
                "value": value,
                "action_id": action["action_id"],
            },
            dry_run,
        )
    ]


def _effect_create_entity(
    root: str,
    state: dict[str, Any],
    action: dict[str, Any],
    effect: dict[str, Any],
    *,
    dry_run: bool,
) -> list[dict[str, Any]]:
    payload = dict(action.get("payload") or {})
    entity_id = str(
        effect.get("entity_id") or payload.get("entity_id") or event_id("entity")
    )
    entity = {
        "id": entity_id,
        "type": str(effect.get("type") or payload.get("type") or "entity"),
        "properties": dict(effect.get("properties") or payload.get("properties") or {}),
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    state.setdefault("entities", {})[entity_id] = entity
    return [
        _event(
            root,
            "entity.created",
            {"entity": entity, "action_id": action["action_id"]},
            dry_run,
        )
    ]


def _matching_consequence_keys(
    rule: dict[str, Any], state: dict[str, Any], events: list[dict[str, Any]]
) -> list[str]:
    when = dict(rule.get("when") or {})
    if "event_type" in when:
        event_type = str(when["event_type"])
        return [
            f"{rule['id']}:event:{event.get('event_id')}"
            for event in events
            if event.get("event_type") == event_type
        ]
    if "entity_property_equals" in when:
        cfg = dict(when["entity_property_equals"] or {})
        matches = []
        for entity_id, entity in dict(state.get("entities") or {}).items():
            if cfg.get("type") and entity.get("type") != cfg.get("type"):
                continue
            if dict(entity.get("properties") or {}).get(cfg.get("property")) == cfg.get(
                "value"
            ):
                matches.append(f"{rule['id']}:entity:{entity_id}:{cfg.get('property')}")
        return matches
    return []


def _event(
    root: str, event_type: str, payload: dict[str, Any], dry_run: bool
) -> dict[str, Any]:
    if dry_run:
        return {
            "schema_version": "droidpuppy.world_event.v1",
            "event_id": event_id(),
            "timestamp": utc_now(),
            "event_type": event_type,
            "source": "droidpuppy.operational_world.dry_run",
            "payload": payload,
        }
    return append_event(
        root, event_type, payload, source="droidpuppy.operational_world"
    )


def _hide_properties(entity: dict[str, Any], hidden: set[str]) -> dict[str, Any]:
    clone = copy.deepcopy(entity)
    props = clone.get("properties")
    if isinstance(props, dict):
        for key in hidden:
            props.pop(key, None)
    return clone


def _matches_any(value: str, patterns: list[str]) -> bool:
    if not patterns:
        return False
    for pattern in patterns:
        pattern = str(pattern)
        if pattern == "*" or pattern == value:
            return True
        if pattern.endswith("*") and value.startswith(pattern[:-1]):
            return True
    return False
