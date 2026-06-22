"""Android reconciliation for the DroidPuppy operational world."""

from __future__ import annotations

import copy
import importlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from .engine import bootstrap_state_from_spec
from .store import append_event, load_spec, load_state, save_state, utc_now


def reconcile_android_world(
    *,
    root: str = "",
    capabilities_json: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Reconcile Android capability facts into durable world entities."""
    capabilities, error = _load_capabilities(capabilities_json)
    if error:
        return {"success": False, "reason": error}

    spec = load_spec(root)
    state = bootstrap_state_from_spec(load_state(root), spec)
    next_state = copy.deepcopy(state)
    summary = _apply_capabilities(next_state, capabilities)
    event_payload = {
        "source_schema": capabilities.get("schema_version", "unknown"),
        "summary": summary,
    }
    event = (
        _dry_event(event_payload)
        if dry_run
        else append_event(
            root,
            "android.reconciled",
            event_payload,
            source="droidpuppy.operational_world",
        )
    )
    if not dry_run:
        save_state(root, next_state)
    return {
        "success": True,
        "dry_run": dry_run,
        "event": event,
        "summary": summary,
        "state_written": not dry_run,
    }


def _load_capabilities(capabilities_json: str) -> tuple[dict[str, Any], str]:
    if capabilities_json.strip():
        try:
            parsed = json.loads(capabilities_json)
        except json.JSONDecodeError as exc:
            return {}, f"capabilities_json is not valid JSON: {exc}"
        if not isinstance(parsed, dict):
            return {}, "capabilities_json must decode to a JSON object"
        return parsed, ""
    try:
        module = _load_android_native_tooling()
        result = module.droidpuppy_android_capabilities()
    except Exception as exc:
        return {}, f"could not load Android capabilities probe: {exc}"
    if not isinstance(result, dict):
        return {}, "Android capabilities probe returned a non-object"
    if not result.get("success", True):
        return {}, str(result.get("reason") or "Android capabilities probe failed")
    return result, ""


def _load_android_native_tooling() -> Any:
    try:
        return importlib.import_module(
            "code_puppy.plugins.droidpuppy_android_native.tooling"
        )
    except Exception:
        pass
    sibling = (
        Path(__file__).resolve().parents[1] / "droidpuppy_android_native" / "tooling.py"
    )
    if not sibling.is_file():
        raise ModuleNotFoundError(
            "droidpuppy_android_native/tooling.py was not found beside operational-world plugin"
        )
    spec = importlib.util.spec_from_file_location(
        "droidpuppy_android_native_tooling_sibling",
        sibling,
    )
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError(f"could not load sibling plugin module: {sibling}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _apply_capabilities(
    state: dict[str, Any], capabilities: dict[str, Any]
) -> dict[str, Any]:
    entities = state.setdefault("entities", {})
    device = (
        capabilities.get("device")
        if isinstance(capabilities.get("device"), dict)
        else {}
    )
    flags = (
        capabilities.get("capability_flags")
        if isinstance(capabilities.get("capability_flags"), dict)
        else {}
    )
    commands = (
        capabilities.get("commands")
        if isinstance(capabilities.get("commands"), dict)
        else {}
    )
    lanes = capabilities.get("recommended_lanes") or []
    graphics = (
        capabilities.get("graphics")
        if isinstance(capabilities.get("graphics"), dict)
        else {}
    )
    security = (
        capabilities.get("security")
        if isinstance(capabilities.get("security"), dict)
        else {}
    )

    _upsert_entity(
        entities,
        "device",
        "android_device",
        {
            "status": "reconciled",
            "manufacturer": device.get("manufacturer", ""),
            "model": device.get("model", ""),
            "android_version": device.get("android_version", ""),
            "sdk": device.get("sdk", ""),
            "abi": device.get("abi", ""),
            "platform": device.get("platform", ""),
            "capability_flags": flags,
            "graphics": graphics,
            "security": {
                "keystore_service_visible": security.get(
                    "keystore_service_visible", False
                ),
                "gatekeeper_service_visible": security.get(
                    "gatekeeper_service_visible", False
                ),
                "native_keystore_bridge_required": security.get(
                    "native_keystore_bridge_required", True
                ),
            },
        },
    )

    command_count = 0
    for command, path in commands.items():
        if not path:
            continue
        command_count += 1
        _upsert_entity(
            entities,
            f"android-command-{command}",
            "android_command",
            {"command": command, "path": path, "available": True},
        )

    lane_count = 0
    for lane in lanes:
        if not isinstance(lane, str) or not lane.strip():
            continue
        lane_count += 1
        _upsert_entity(
            entities,
            f"lane-{lane}",
            "lane",
            {
                "lane": lane,
                "source": "android.capabilities.v1",
                "status": "recommended",
            },
        )

    state["updated_at"] = utc_now()
    return {
        "device_entity": "device",
        "command_entities": command_count,
        "lane_entities": lane_count,
        "android_native_available": bool(flags.get("android_native_available")),
        "arm64": bool(flags.get("arm64")),
    }


def _upsert_entity(
    entities: dict[str, Any],
    entity_id: str,
    entity_type: str,
    properties: dict[str, Any],
) -> None:
    now = utc_now()
    entity = entities.setdefault(
        entity_id,
        {
            "id": entity_id,
            "type": entity_type,
            "properties": {},
            "created_at": now,
            "updated_at": now,
        },
    )
    entity["type"] = entity_type
    entity.setdefault("properties", {}).update(properties)
    entity["updated_at"] = now


def _dry_event(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "droidpuppy.world_event.v1",
        "event_id": "dry-run-android-reconciled",
        "timestamp": utc_now(),
        "event_type": "android.reconciled",
        "source": "droidpuppy.operational_world.dry_run",
        "payload": payload,
    }
