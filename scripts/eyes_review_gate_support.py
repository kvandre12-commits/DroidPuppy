from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_ROOT = REPO_ROOT / "contracts"
V1_CONTRACTS_DIR = CONTRACTS_ROOT / "v1"
V2_CONTRACTS_DIR = CONTRACTS_ROOT / "v2"
DEFAULT_ROOT = Path.home() / ".project_os" / "eyes"
DEFAULT_LEASE_MINUTES = 15
DEFAULT_PRINCIPAL_ID = os.environ.get("PROJECT_OS_PRINCIPAL_ID", "code-puppy-41abae")
DEFAULT_LEASE_SCOPE = "single_harmless_action"
DEFAULT_LEASE_CAPABILITIES = [
    "android.app.launch",
    "android.browser.open_url",
    "android.notification.post",
    "android.settings.open",
]


@dataclass(frozen=True)
class ReviewPaths:
    root: Path
    review_dir: Path
    review_pending: Path
    review_approved: Path
    review_rejected: Path
    latest_review: Path
    leases_dir: Path
    leases_active: Path
    audit_dir: Path
    audit_events: Path


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_paths(root: str | Path | None = None) -> ReviewPaths:
    base = Path(root).expanduser().resolve() if root else DEFAULT_ROOT
    review_dir = base / "review"
    return ReviewPaths(
        root=base,
        review_dir=review_dir,
        review_pending=review_dir / "pending",
        review_approved=review_dir / "approved",
        review_rejected=review_dir / "rejected",
        latest_review=review_dir / "review_required.json",
        leases_dir=base / "leases",
        leases_active=base / "leases" / "active",
        audit_dir=base / "audit",
        audit_events=base / "audit" / "events",
    )


def ensure_layout(root: str | Path | None = None) -> ReviewPaths:
    paths = resolve_paths(root)
    for path in (
        paths.root,
        paths.review_dir,
        paths.review_pending,
        paths.review_approved,
        paths.review_rejected,
        paths.leases_dir,
        paths.leases_active,
        paths.audit_dir,
        paths.audit_events,
    ):
        path.mkdir(parents=True, exist_ok=True)
    return paths


def schema_dir(version: str) -> Path:
    if version == "v2":
        return V2_CONTRACTS_DIR
    return V1_CONTRACTS_DIR


def load_schema(name: str, *, version: str = "v1") -> dict[str, Any]:
    return json.loads((schema_dir(version) / name).read_text())


def validate(payload: dict[str, Any], schema_name: str, *, version: str = "v1") -> None:
    jsonschema.validate(payload, load_schema(schema_name, version=version))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_json_new(path: Path, payload: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def previous_event_sha(paths: ReviewPaths) -> str | None:
    events = sorted(paths.audit_events.glob("*.json"))
    if not events:
        return None
    latest = read_json(events[-1])
    value = latest.get("event_sha256")
    return str(value) if value else None


def emit_audit_event(
    paths: ReviewPaths,
    *,
    event_type: str,
    principal_id: str | None = None,
    lease_id: str | None = None,
    capability: str | None = None,
    tool_name: str | None = None,
    outcome: str | None = None,
    reason: str = "",
    details: dict[str, Any] | None = None,
) -> Path:
    timestamp_ns = time.time_ns()
    event_core = {
        "contract_version": "2.0.0",
        "event_id": uid("audit"),
        "event_type": event_type,
        "principal_id": principal_id,
        "lease_id": lease_id,
        "capability": capability,
        "tool_name": tool_name,
        "outcome": outcome,
        "reason": reason,
        "details": details or {},
        "timestamp": now_iso(),
        "timestamp_ns": timestamp_ns,
        "previous_event_sha256": previous_event_sha(paths),
    }
    event = dict(event_core)
    event["event_sha256"] = sha256_text(canonical_json(event_core))
    validate(event, "eyes_audit_event.schema.json", version="v2")
    event_path = paths.audit_events / f"{timestamp_ns}_{event['event_id']}.json"
    write_json_new(event_path, event)
    return event_path


def normalize_list(values: list[str] | None) -> list[str]:
    cleaned: list[str] = []
    for value in values or []:
        text = str(value).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def quota_payload(
    *,
    max_uses: int,
    max_tool_calls: int | None,
    max_shell_commands: int | None,
    max_token_spend: int | None,
) -> dict[str, Any]:
    resolved_tool_calls = max_tool_calls if max_tool_calls is not None else max_uses
    return {
        "max_uses": max_uses,
        "remaining_uses": max_uses,
        "max_tool_calls": resolved_tool_calls,
        "max_shell_commands": max_shell_commands,
        "max_token_spend": max_token_spend,
        "tool_calls_used": 0,
        "shell_commands_used": 0,
        "token_spend_used": 0,
    }


def mint_execution_lease(
    paths: ReviewPaths,
    review: dict[str, Any],
    *,
    decided_by: str,
    principal_id: str,
    capabilities: list[str],
    allowed_tools: list[str],
    lease_scope: str,
    audit_event_ref: Path,
    lease_minutes: int,
    max_uses: int,
    max_tool_calls: int | None,
    max_shell_commands: int | None,
    max_token_spend: int | None,
) -> tuple[Path, Path]:
    created_at = dt.datetime.now(dt.timezone.utc)
    expires_at = created_at + dt.timedelta(minutes=lease_minutes)
    lease = {
        "contract_version": "2.0.0",
        "lease_id": uid("lease"),
        "review_id": str(review["review_id"]),
        "result_id": str(review["result_id"]),
        "artifact_id": str(review["artifact_id"]),
        "worker_class": str(review["worker_class"]),
        "issued_by": decided_by,
        "principal_id": principal_id,
        "lease_scope": lease_scope,
        "capabilities": capabilities,
        "allowed_tools": allowed_tools,
        "constraints": {},
        "quotas": quota_payload(
            max_uses=max_uses,
            max_tool_calls=max_tool_calls,
            max_shell_commands=max_shell_commands,
            max_token_spend=max_token_spend,
        ),
        "status": "active",
        "decision_event_ref": str(audit_event_ref),
        "minted_event_ref": None,
        "created_at": created_at.isoformat(),
        "not_before": created_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "last_used_at": None,
        "revoked_at": None,
        "revoked_by": None,
        "revocation_reason": None,
    }
    validate(lease, "eyes_execution_lease.schema.json", version="v2")
    lease_path = paths.leases_active / f"{lease['lease_id']}.json"
    write_json_new(lease_path, lease)

    minted_event_path = emit_audit_event(
        paths,
        event_type="lease_minted",
        principal_id=principal_id,
        lease_id=str(lease["lease_id"]),
        outcome="minted",
        reason="Lease minted after explicit operator approval.",
        details={
            "review_id": review["review_id"],
            "artifact_id": review["artifact_id"],
            "capabilities": capabilities,
            "allowed_tools": allowed_tools,
            "lease_ref": str(lease_path),
            "decision_event_ref": str(audit_event_ref),
            "quotas": lease["quotas"],
        },
    )
    lease["minted_event_ref"] = str(minted_event_path)
    validate(lease, "eyes_execution_lease.schema.json", version="v2")
    write_json(lease_path, lease)
    return lease_path, minted_event_path
