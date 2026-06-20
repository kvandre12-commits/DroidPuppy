#!/usr/bin/env python3
"""Minimal human-review gate for the eyes worker lane."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shlex
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = REPO_ROOT / "contracts" / "v1"
DEFAULT_ROOT = Path.home() / ".project_os" / "eyes"
DEFAULT_LEASE_MINUTES = 15


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


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
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


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((CONTRACTS_DIR / name).read_text())


def _validate(payload: dict[str, Any], schema_name: str) -> None:
    jsonschema.validate(payload, _load_schema(schema_name))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_json_new(path: Path, payload: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _run_command(args: list[str], timeout: int = 20) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": True,
            "args": args,
            "exit_code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "args": args,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "error": f"command not found: {exc}",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "args": args,
            "exit_code": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "error": f"command timed out after {timeout}s",
        }


def _notification_title(review: dict[str, Any]) -> str:
    return f"Review Required: {review['artifact_id']}"


def _notification_body(review: dict[str, Any]) -> str:
    worker_class = str(review["worker_class"]).replace("_", " ").title()
    return "\n".join(
        [
            "Artifact Ready",
            f"Type: {worker_class}",
            f"ID: {review['artifact_id']}",
            "Action Required",
        ]
    )


def _notification_action(review_path: Path) -> str | None:
    termux_open = shutil.which("termux-open")
    if not termux_open:
        return None
    return f"{shlex.quote(termux_open)} {shlex.quote(str(review_path))}"


def _send_notification(review: dict[str, Any], review_path: Path) -> dict[str, Any]:
    termux_notification = shutil.which("termux-notification")
    if not termux_notification:
        return {
            "success": False,
            "mode": "unavailable",
            "message": "termux-notification is not available.",
        }
    command = [
        termux_notification,
        "--id",
        str(abs(hash(str(review["review_id"]))) % 100000),
        "--title",
        str(review["title"]),
        "--content",
        str(review["body"]),
        "--priority",
        "high",
    ]
    action = _notification_action(review_path)
    if action:
        command.extend(["--action", action])
    result = _run_command(command)
    return {
        "success": result.get("exit_code") == 0,
        "mode": "termux-notification",
        "command": command,
        "result": result,
        "tap_action": action,
    }


def emit_review_required(
    result: dict[str, Any],
    result_path: str | Path,
    *,
    root: str | Path | None = None,
    notify: bool = True,
) -> dict[str, Any]:
    paths = ensure_layout(root)
    review_id = _uid("review")
    review_path = paths.review_pending / f"{review_id}.json"
    review = {
        "contract_version": "1.0.0",
        "review_id": review_id,
        "result_id": str(result["result_id"]),
        "result_ref": str(Path(result_path).resolve()),
        "queue_item_id": str(result["queue_item_id"]),
        "artifact_id": str(result["artifact_id"]),
        "worker_class": str(result["worker_class"]),
        "title": _notification_title({"artifact_id": result["artifact_id"]}),
        "body": _notification_body(
            {
                "artifact_id": result["artifact_id"],
                "worker_class": result["worker_class"],
            }
        ),
        "action_required": str(result["next_action"]),
        "status": "pending",
        "source_artifact_path": result.get("source_artifact_path"),
        "open_target": str(review_path),
        "created_at": _now(),
        "decided_at": None,
        "decided_by": None,
        "decision_reason": None,
        "audit_event_ref": None,
        "lease_ref": None,
    }
    _validate(review, "eyes_review_required.schema.json")
    _write_json(review_path, review)
    _write_json(paths.latest_review, review)
    notification = None
    if notify:
        notification = _send_notification(review, review_path)
    return {
        "review_ref": str(review_path),
        "latest_review_ref": str(paths.latest_review),
        "notification": notification,
    }


def _resolve_pending_review_path(paths: ReviewPaths, review_id: str) -> Path:
    normalized = Path(review_id).stem
    direct = paths.review_pending / f"{normalized}.json"
    if direct.is_file():
        return direct
    for candidate in paths.review_pending.glob("*.json"):
        payload = _read_json(candidate)
        if str(payload.get("review_id", "")) == normalized:
            return candidate
    raise FileNotFoundError(f"Pending review not found: {review_id}")


def _previous_event_sha(paths: ReviewPaths) -> str | None:
    events = sorted(paths.audit_events.glob("*.json"))
    if not events:
        return None
    latest = _read_json(events[-1])
    value = latest.get("event_sha256")
    return str(value) if value else None


def _emit_audit_event(
    paths: ReviewPaths,
    review_snapshot: dict[str, Any],
    review_ref: Path,
    *,
    decision: str,
    decided_by: str,
    reason: str,
) -> Path:
    timestamp_ns = time.time_ns()
    event_core = {
        "contract_version": "1.0.0",
        "event_id": _uid("audit"),
        "event_type": "review_decision",
        "decision": decision,
        "review_ref": str(review_ref),
        "review_sha256": _sha256_text(_canonical_json(review_snapshot)),
        "review_artifact": review_snapshot,
        "decided_by": decided_by,
        "decision_reason": reason,
        "timestamp": _now(),
        "timestamp_ns": timestamp_ns,
        "previous_event_sha256": _previous_event_sha(paths),
    }
    event_hash = _sha256_text(_canonical_json(event_core))
    event = dict(event_core)
    event["event_sha256"] = event_hash
    _validate(event, "eyes_audit_event.schema.json")
    event_path = paths.audit_events / f"{timestamp_ns}_{event['event_id']}.json"
    _write_json_new(event_path, event)
    return event_path


def _mint_execution_lease(
    paths: ReviewPaths,
    review: dict[str, Any],
    *,
    decided_by: str,
    audit_event_ref: Path,
    lease_minutes: int,
) -> Path:
    created_at = dt.datetime.now(dt.timezone.utc)
    expires_at = created_at + dt.timedelta(minutes=lease_minutes)
    lease = {
        "contract_version": "1.0.0",
        "lease_id": _uid("lease"),
        "review_id": str(review["review_id"]),
        "result_id": str(review["result_id"]),
        "artifact_id": str(review["artifact_id"]),
        "worker_class": str(review["worker_class"]),
        "issued_by": decided_by,
        "lease_scope": "single_harmless_action",
        "max_uses": 1,
        "remaining_uses": 1,
        "status": "active",
        "decision_event_ref": str(audit_event_ref),
        "created_at": created_at.isoformat(),
        "expires_at": expires_at.isoformat(),
    }
    _validate(lease, "eyes_execution_lease.schema.json")
    lease_path = paths.leases_active / f"{lease['lease_id']}.json"
    _write_json_new(lease_path, lease)
    return lease_path


def list_pending_reviews(root: str | Path | None = None) -> list[dict[str, Any]]:
    paths = ensure_layout(root)
    reviews: list[dict[str, Any]] = []
    for path in sorted(paths.review_pending.glob("*.json")):
        payload = _read_json(path)
        _validate(payload, "eyes_review_required.schema.json")
        reviews.append(
            {
                "review_id": payload["review_id"],
                "artifact_id": payload["artifact_id"],
                "worker_class": payload["worker_class"],
                "created_at": payload["created_at"],
                "path": str(path),
            }
        )
    return reviews


def decide_review(
    review_id: str,
    *,
    approve: bool,
    root: str | Path | None = None,
    decided_by: str = "operator",
    reason: str = "",
    lease_minutes: int = DEFAULT_LEASE_MINUTES,
) -> dict[str, Any]:
    if lease_minutes < 1:
        raise ValueError("lease_minutes must be at least 1")
    paths = ensure_layout(root)
    pending_path = _resolve_pending_review_path(paths, review_id)
    original_review = _read_json(pending_path)
    _validate(original_review, "eyes_review_required.schema.json")

    decision = "APPROVED" if approve else "REJECTED"
    audit_event_path = _emit_audit_event(
        paths,
        original_review,
        pending_path,
        decision=decision,
        decided_by=decided_by,
        reason=reason,
    )

    updated_review = dict(original_review)
    updated_review["status"] = "approved" if approve else "rejected"
    updated_review["decided_at"] = _now()
    updated_review["decided_by"] = decided_by
    updated_review["decision_reason"] = reason
    updated_review["audit_event_ref"] = str(audit_event_path)

    lease_path = None
    if approve:
        lease_path = _mint_execution_lease(
            paths,
            updated_review,
            decided_by=decided_by,
            audit_event_ref=audit_event_path,
            lease_minutes=lease_minutes,
        )
        updated_review["lease_ref"] = str(lease_path)
        destination = paths.review_approved / pending_path.name
    else:
        updated_review["lease_ref"] = None
        destination = paths.review_rejected / pending_path.name

    updated_review["open_target"] = str(destination)
    _validate(updated_review, "eyes_review_required.schema.json")
    _write_json_new(destination, updated_review)
    pending_path.unlink()
    _write_json(paths.latest_review, updated_review)

    return {
        "success": True,
        "decision": decision,
        "review_ref": str(destination),
        "audit_event_ref": str(audit_event_path),
        "lease_ref": str(lease_path) if lease_path else None,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Eyes review gate")
    parser.add_argument(
        "--root",
        help="Override the eyes root directory (default: ~/.project_os/eyes).",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--approve", help="Approve the given pending review id.")
    group.add_argument("--reject", help="Reject the given pending review id.")
    group.add_argument(
        "--list-pending",
        action="store_true",
        help="List pending review artifacts and exit.",
    )
    parser.add_argument(
        "--decided-by",
        default="operator",
        help="Operator identity to stamp into the decision and lease.",
    )
    parser.add_argument(
        "--reason",
        default="",
        help="Optional human decision reason to preserve in the audit event.",
    )
    parser.add_argument(
        "--lease-minutes",
        type=int,
        default=DEFAULT_LEASE_MINUTES,
        help="Lease lifetime in minutes for approvals (default: 15).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.list_pending:
            print(
                json.dumps(
                    {"pending_reviews": list_pending_reviews(args.root)}, indent=2
                )
            )
            return 0
        if args.approve:
            print(
                json.dumps(
                    decide_review(
                        args.approve,
                        approve=True,
                        root=args.root,
                        decided_by=args.decided_by,
                        reason=args.reason,
                        lease_minutes=args.lease_minutes,
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.reject:
            print(
                json.dumps(
                    decide_review(
                        args.reject,
                        approve=False,
                        root=args.root,
                        decided_by=args.decided_by,
                        reason=args.reason,
                        lease_minutes=args.lease_minutes,
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"success": False, "error": repr(exc)}))
        return 1
    parser.error("No action selected")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
