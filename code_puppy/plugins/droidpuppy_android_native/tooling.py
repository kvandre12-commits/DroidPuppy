"""DroidPuppy Android-native surface tooling.

This module exposes the first real Android-native seam for Project OS:

- ``android.capabilities.v1``: read-only hardware/platform/security probe
- ``android.event_bridge.v1``: append-only JSONL event publication
- ``android.approval_receipt.v1``: canonical approval receipt envelope

Important: Python/Termux cannot honestly create Android hardware-backed
Keystore signatures by itself. The receipt helper therefore supports a local
HMAC development backend and explicitly reports ``hardware_backed=False``.
A future native Android bridge should sign the same canonical payload through
Android Keystore / KeyMint and flip the backend metadata accordingly.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_CAPABILITIES = "android.capabilities.v1"
SCHEMA_EVENT = "android.event_bridge.v1"
SCHEMA_APPROVAL = "android.approval_receipt.v1"
DEFAULT_EVENT_LOG = "outputs/droidpuppy_android_events.jsonl"

_PROP_KEYS = [
    "ro.product.manufacturer",
    "ro.product.model",
    "ro.board.platform",
    "ro.hardware",
    "ro.soc.manufacturer",
    "ro.soc.model",
    "ro.product.cpu.abi",
    "ro.build.version.release",
    "ro.build.version.sdk",
    "ro.hardware.keystore",
    "ro.security.keystore.keytype",
]

_SECURITY_SERVICES = (
    "keystore",
    "keymint",
    "gatekeeper",
    "tee",
    "strongbox",
)

_MEDIA_SERVICES = (
    "camera",
    "media",
    "sensor",
)

_GPU_HINTS = (
    "adreno",
    "qualcomm",
    "gles",
    "egl",
    "vulkan",
)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _resolve_command(command: str) -> str:
    found = shutil.which(command)
    if found:
        return found
    system_path = Path("/system/bin") / command
    if system_path.exists():
        return str(system_path)
    return command


def _run_command(args: list[str], timeout: int = 5) -> dict[str, Any]:
    resolved_args = [_resolve_command(args[0]), *args[1:]] if args else args
    try:
        proc = subprocess.run(
            resolved_args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": True,
            "args": resolved_args,
            "exit_code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "args": resolved_args,
            "error": f"command not found: {exc}",
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "args": resolved_args,
            "error": f"timed out after {timeout}s",
        }


def _getprop(name: str) -> str:
    result = _run_command(["getprop", name])
    return str(result.get("stdout") or "").strip() if result.get("ok") else ""


def _grep_lines(text: str, needles: tuple[str, ...], *, limit: int) -> list[str]:
    rows: list[str] = []
    lowered_needles = tuple(item.lower() for item in needles)
    for line in text.splitlines():
        lowered = line.lower()
        if any(item in lowered for item in lowered_needles):
            rows.append(line.strip())
        if len(rows) >= limit:
            break
    return rows


def _service_lines(needles: tuple[str, ...], *, limit: int = 80) -> list[str]:
    result = _run_command(["service", "list"])
    if not result.get("ok"):
        return []
    return _grep_lines(str(result.get("stdout") or ""), needles, limit=limit)


def _surfaceflinger_gpu_hints() -> list[str]:
    result = _run_command(["dumpsys", "SurfaceFlinger"], timeout=8)
    if not result.get("ok"):
        return []
    return _grep_lines(str(result.get("stdout") or ""), _GPU_HINTS, limit=40)


def _command_map(commands: list[str]) -> dict[str, str]:
    return {
        command: path if (path := _resolve_command(command)) != command else ""
        for command in commands
    }


def droidpuppy_android_capabilities() -> dict[str, Any]:
    """Probe Android-native capabilities without mutating device state."""

    props = {key: _getprop(key) for key in _PROP_KEYS}
    android_version = props.get("ro.build.version.release", "")
    sdk = props.get("ro.build.version.sdk", "")
    is_android = bool(android_version or sdk)
    security_services = _service_lines(_SECURITY_SERVICES)
    media_services = _service_lines(_MEDIA_SERVICES)
    gpu_hints = _surfaceflinger_gpu_hints()
    commands = _command_map(["am", "pm", "cmd", "dumpsys", "service", "getprop"])

    key_types = [
        item.strip()
        for item in props.get("ro.security.keystore.keytype", "").split(",")
        if item.strip()
    ]
    keystore_running = any("keystore" in line.lower() for line in security_services)
    gatekeeper_running = any("gatekeeper" in line.lower() for line in security_services)

    capability_flags = {
        "android_native_available": is_android,
        "arm64": props.get("ro.product.cpu.abi") == "arm64-v8a",
        "qualcomm_family": any(
            "qcom" in props.get(key, "").lower()
            or "qti" in props.get(key, "").lower()
            or "sm" in props.get(key, "").lower()
            for key in ("ro.hardware", "ro.soc.manufacturer", "ro.soc.model")
        ),
        "hardware_keystore_service_visible": keystore_running,
        "gatekeeper_service_visible": gatekeeper_running,
        "media_services_visible": bool(media_services),
        "gpu_hints_visible": bool(gpu_hints),
    }

    recommended_lanes = [
        "trust_lane" if keystore_running else "trust_lane_probe_native_bridge_needed",
        "event_lane",
        "survival_lane",
    ]
    if media_services:
        recommended_lanes.append("perception_lane")
    if gpu_hints or capability_flags["qualcomm_family"]:
        recommended_lanes.append("acceleration_lane")

    return {
        "success": True,
        "schema_version": SCHEMA_CAPABILITIES,
        "timestamp": _utc_now(),
        "device": {
            "manufacturer": props.get("ro.product.manufacturer", ""),
            "model": props.get("ro.product.model", ""),
            "platform": props.get("ro.board.platform", ""),
            "hardware": props.get("ro.hardware", ""),
            "soc_manufacturer": props.get("ro.soc.manufacturer", ""),
            "soc_model": props.get("ro.soc.model", ""),
            "abi": props.get("ro.product.cpu.abi", ""),
            "android_version": android_version,
            "sdk": sdk,
        },
        "commands": commands,
        "security": {
            "services": security_services,
            "keystore_hardware": props.get("ro.hardware.keystore", ""),
            "keystore_key_types": key_types,
            "keystore_service_visible": keystore_running,
            "gatekeeper_service_visible": gatekeeper_running,
            "hardware_backed_python_signing_available": False,
            "native_keystore_bridge_required": True,
        },
        "media": {"services": media_services},
        "graphics": {
            "gpu_hints": gpu_hints,
            "adreno_or_qualcomm_likely": capability_flags["qualcomm_family"]
            or any("adreno" in line.lower() for line in gpu_hints),
        },
        "capability_flags": capability_flags,
        "recommended_lanes": recommended_lanes,
    }


def _parse_payload_json(payload_json: str) -> tuple[dict[str, Any] | None, str]:
    if not payload_json.strip():
        return {}, ""
    try:
        parsed = json.loads(payload_json)
    except json.JSONDecodeError as exc:
        return None, f"payload_json is not valid JSON: {exc}"
    if not isinstance(parsed, dict):
        return None, "payload_json must decode to a JSON object"
    return parsed, ""


def _append_jsonl(path: str, envelope: dict[str, Any]) -> str:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(envelope, sort_keys=True) + "\n")
    return str(target)


def droidpuppy_android_event_publish(
    event_type: str,
    payload_json: str = "{}",
    *,
    topic: str = "android.native",
    source: str = "droidpuppy.android_native",
    output_path: str = DEFAULT_EVENT_LOG,
    publish_to_project_os_bus: bool = True,
) -> dict[str, Any]:
    """Append an Android-native event and best-effort publish to Project OS bus."""

    if not event_type.strip():
        return {"success": False, "reason": "event_type is required"}
    payload, error = _parse_payload_json(payload_json)
    if error or payload is None:
        return {"success": False, "reason": error}

    envelope = {
        "schema_version": SCHEMA_EVENT,
        "event_id": f"android-native-{uuid.uuid4().hex[:12]}",
        "timestamp": _utc_now(),
        "topic": topic.strip() or "android.native",
        "event_type": event_type.strip(),
        "source": source.strip() or "droidpuppy.android_native",
        "payload": payload,
    }
    written_path = _append_jsonl(output_path, envelope)

    bus_envelope = None
    if publish_to_project_os_bus:
        try:
            from code_puppy.plugins.project_os_supervisor.bus import (
                publish_project_os_event_best_effort,
            )

            bus_envelope = publish_project_os_event_best_effort(
                envelope["topic"],
                envelope["event_type"],
                source=envelope["source"],
                payload=envelope,
            )
        except Exception:
            bus_envelope = None

    return {
        "success": True,
        "schema_version": SCHEMA_EVENT,
        "event": envelope,
        "event_log_path": written_path,
        "project_os_bus_published": bus_envelope is not None,
        "project_os_bus_event": bus_envelope,
    }


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _dev_signing_key(secret: str = "") -> bytes:
    supplied = secret or os.environ.get("DROIDPUPPY_DEV_SIGNING_KEY", "")
    if supplied:
        return supplied.encode("utf-8")
    material = f"{os.getuid()}:{Path.home()}:{SCHEMA_APPROVAL}"
    return hashlib.sha256(material.encode("utf-8")).digest()


def _verify_hmac_signature(
    canonical_json: str,
    signature_value: str,
    *,
    dev_secret: str = "",
) -> bool:
    expected = hmac.new(
        _dev_signing_key(dev_secret),
        canonical_json.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_value)


def droidpuppy_android_approval_receipt(
    principal_id: str,
    capability: str,
    action: str,
    reason: str,
    *,
    risk_tier: str = "review_required",
    ttl_seconds: int = 60,
    nonce: str = "",
    signing_backend: str = "local-hmac-dev",
    dev_secret: str = "",
) -> dict[str, Any]:
    """Create a canonical approval receipt envelope.

    ``local-hmac-dev`` is intentionally not hardware-backed. It provides a
    deterministic development envelope that Project OS can verify while the
    native Android Keystore bridge is being built.
    """

    missing = [
        name
        for name, value in {
            "principal_id": principal_id,
            "capability": capability,
            "action": action,
            "reason": reason,
        }.items()
        if not value.strip()
    ]
    if missing:
        return {
            "success": False,
            "reason": f"missing required fields: {', '.join(missing)}",
        }
    if signing_backend != "local-hmac-dev":
        return {
            "success": False,
            "reason": "Only local-hmac-dev is available in the Termux bridge; native Keystore signer is next.",
            "native_keystore_bridge_required": True,
        }

    issued_at = _utc_now()
    receipt = {
        "schema_version": SCHEMA_APPROVAL,
        "receipt_id": f"approval-{uuid.uuid4().hex[:12]}",
        "issued_at": issued_at,
        "principal_id": principal_id.strip(),
        "capability": capability.strip(),
        "action": action.strip(),
        "reason": reason.strip(),
        "risk_tier": risk_tier.strip() or "review_required",
        "ttl_seconds": max(1, int(ttl_seconds)),
        "nonce": nonce.strip() or uuid.uuid4().hex,
    }
    canonical = _canonical_json(receipt)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    signature = hmac.new(
        _dev_signing_key(dev_secret), canonical.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return {
        "success": True,
        "schema_version": SCHEMA_APPROVAL,
        "receipt": receipt,
        "canonical_json": canonical,
        "canonical_sha256": digest,
        "signature": {
            "algorithm": "HMAC-SHA256",
            "backend": signing_backend,
            "hardware_backed": False,
            "value": signature,
            "native_keystore_bridge_required": True,
        },
        "verification_hint": "Verify HMAC over canonical_json for dev; replace with Android Keystore signature in native bridge.",
    }


def droidpuppy_android_verify_approval_receipt(
    receipt_json: str,
    *,
    dev_secret: str = "",
    require_hardware_backed: bool = False,
) -> dict[str, Any]:
    """Verify an ``android.approval_receipt.v1`` envelope.

    The current Termux verifier supports the local development HMAC backend.
    Future Android Keystore signatures should be verified by a native bridge or
    platform verifier, not guessed in Python.
    """

    try:
        envelope = json.loads(receipt_json)
    except json.JSONDecodeError as exc:
        return {"success": False, "valid": False, "reason": f"invalid JSON: {exc}"}
    if not isinstance(envelope, dict):
        return {
            "success": False,
            "valid": False,
            "reason": "receipt_json must be an object",
        }
    if envelope.get("schema_version") != SCHEMA_APPROVAL:
        return {
            "success": False,
            "valid": False,
            "reason": f"schema_version must be {SCHEMA_APPROVAL}",
        }

    canonical_json = str(envelope.get("canonical_json") or "")
    supplied_digest = str(envelope.get("canonical_sha256") or "")
    signature = envelope.get("signature")
    if not canonical_json or not supplied_digest or not isinstance(signature, dict):
        return {
            "success": False,
            "valid": False,
            "reason": "canonical_json, canonical_sha256, and signature are required",
        }

    actual_digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(actual_digest, supplied_digest):
        return {
            "success": True,
            "valid": False,
            "reason": "canonical_sha256 mismatch",
            "actual_sha256": actual_digest,
        }

    hardware_backed = bool(signature.get("hardware_backed"))
    if require_hardware_backed and not hardware_backed:
        return {
            "success": True,
            "valid": False,
            "reason": "hardware-backed signature required",
            "native_keystore_bridge_required": True,
        }

    backend = str(signature.get("backend") or "")
    signature_value = str(signature.get("value") or "")
    if backend == "local-hmac-dev":
        valid = _verify_hmac_signature(
            canonical_json,
            signature_value,
            dev_secret=dev_secret,
        )
        return {
            "success": True,
            "valid": valid,
            "backend": backend,
            "hardware_backed": False,
            "reason": "ok" if valid else "local HMAC signature mismatch",
        }

    return {
        "success": True,
        "valid": False,
        "backend": backend,
        "hardware_backed": hardware_backed,
        "reason": "native signature verifier is not implemented in Termux bridge",
        "native_keystore_bridge_required": True,
    }
