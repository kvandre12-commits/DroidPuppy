#!/usr/bin/env python3
"""Minimal human-review gate for the eyes worker lane."""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

from eyes_review_gate_support import (
    DEFAULT_LEASE_CAPABILITIES,
    DEFAULT_LEASE_MINUTES,
    DEFAULT_LEASE_SCOPE,
    DEFAULT_PRINCIPAL_ID,
    canonical_json,
    emit_audit_event,
    ensure_layout,
    mint_execution_lease,
    normalize_constraints,
    normalize_list,
    now_iso,
    read_json,
    resolve_paths,
    sha256_text,
    uid,
    validate,
    write_json,
    write_json_new,
)


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
    review_id = uid("review")
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
        "created_at": now_iso(),
        "decided_at": None,
        "decided_by": None,
        "decision_reason": None,
        "audit_event_ref": None,
        "lease_ref": None,
    }
    validate(review, "eyes_review_required.schema.json")
    write_json(review_path, review)
    write_json(paths.latest_review, review)
    notification = _send_notification(review, review_path) if notify else None
    return {
        "review_ref": str(review_path),
        "latest_review_ref": str(paths.latest_review),
        "notification": notification,
    }


def _resolve_pending_review_path(
    review_id: str, *, root: str | Path | None = None
) -> Path:
    paths = resolve_paths(root)
    normalized = Path(review_id).stem
    direct = paths.review_pending / f"{normalized}.json"
    if direct.is_file():
        return direct
    for candidate in paths.review_pending.glob("*.json"):
        payload = read_json(candidate)
        if str(payload.get("review_id", "")) == normalized:
            return candidate
    raise FileNotFoundError(f"Pending review not found: {review_id}")


def list_pending_reviews(root: str | Path | None = None) -> list[dict[str, Any]]:
    paths = ensure_layout(root)
    reviews: list[dict[str, Any]] = []
    for path in sorted(paths.review_pending.glob("*.json")):
        payload = read_json(path)
        validate(payload, "eyes_review_required.schema.json")
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
    principal_id: str = DEFAULT_PRINCIPAL_ID,
    capabilities: list[str] | None = None,
    allowed_tools: list[str] | None = None,
    allowed_paths: list[str] | None = None,
    intent_actions: list[str] | None = None,
    intent_packages: list[str] | None = None,
    browser_packages: list[str] | None = None,
    constraint_notes: str = "",
    lease_scope: str = DEFAULT_LEASE_SCOPE,
    max_uses: int = 1,
    max_tool_calls: int | None = None,
    max_shell_commands: int | None = None,
    max_token_spend: int | None = None,
) -> dict[str, Any]:
    if lease_minutes < 1:
        raise ValueError("lease_minutes must be at least 1")
    if max_uses < 1:
        raise ValueError("max_uses must be at least 1")
    if max_tool_calls is not None and max_tool_calls < 0:
        raise ValueError("max_tool_calls cannot be negative")
    if max_shell_commands is not None and max_shell_commands < 0:
        raise ValueError("max_shell_commands cannot be negative")
    if max_token_spend is not None and max_token_spend < 0:
        raise ValueError("max_token_spend cannot be negative")

    resolved_capabilities = normalize_list(capabilities) or list(
        DEFAULT_LEASE_CAPABILITIES
    )
    resolved_tools = normalize_list(allowed_tools)
    resolved_constraints = normalize_constraints(
        allowed_paths=allowed_paths,
        intent_actions=intent_actions,
        intent_packages=intent_packages,
        browser_packages=browser_packages,
        notes=constraint_notes,
    )

    paths = ensure_layout(root)
    pending_path = _resolve_pending_review_path(review_id, root=root)
    original_review = read_json(pending_path)
    validate(original_review, "eyes_review_required.schema.json")

    decision = "APPROVED" if approve else "REJECTED"
    audit_event_path = emit_audit_event(
        paths,
        event_type="review_decision",
        principal_id=principal_id,
        outcome=decision,
        reason=reason,
        details={
            "review_ref": str(pending_path),
            "review_sha256": sha256_text(canonical_json(original_review)),
            "review_artifact": original_review,
            "decision": decision,
            "decided_by": decided_by,
            "decision_reason": reason,
        },
    )

    updated_review = dict(original_review)
    updated_review["status"] = "approved" if approve else "rejected"
    updated_review["decided_at"] = now_iso()
    updated_review["decided_by"] = decided_by
    updated_review["decision_reason"] = reason
    updated_review["audit_event_ref"] = str(audit_event_path)

    lease_path = None
    lease_audit_event_path = None
    if approve:
        lease_path, lease_audit_event_path = mint_execution_lease(
            paths,
            updated_review,
            decided_by=decided_by,
            principal_id=principal_id,
            capabilities=resolved_capabilities,
            allowed_tools=resolved_tools,
            constraints=resolved_constraints,
            lease_scope=lease_scope,
            audit_event_ref=audit_event_path,
            lease_minutes=lease_minutes,
            max_uses=max_uses,
            max_tool_calls=max_tool_calls,
            max_shell_commands=max_shell_commands,
            max_token_spend=max_token_spend,
        )
        updated_review["lease_ref"] = str(lease_path)
        destination = paths.review_approved / pending_path.name
    else:
        updated_review["lease_ref"] = None
        destination = paths.review_rejected / pending_path.name

    updated_review["open_target"] = str(destination)
    validate(updated_review, "eyes_review_required.schema.json")
    write_json_new(destination, updated_review)
    pending_path.unlink()
    write_json(paths.latest_review, updated_review)

    return {
        "success": True,
        "decision": decision,
        "review_ref": str(destination),
        "audit_event_ref": str(audit_event_path),
        "lease_ref": str(lease_path) if lease_path else None,
        "lease_audit_event_ref": (
            str(lease_audit_event_path) if lease_audit_event_path else None
        ),
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
    parser.add_argument(
        "--principal-id",
        default=DEFAULT_PRINCIPAL_ID,
        help="Principal id to bind into the minted lease.",
    )
    parser.add_argument(
        "--lease-scope",
        default=DEFAULT_LEASE_SCOPE,
        help="Lease scope label preserved for backward compatibility and operator readability.",
    )
    parser.add_argument(
        "--capability",
        action="append",
        dest="capabilities",
        help="Capability to grant. Repeatable. Defaults to harmless Android launch capabilities when omitted.",
    )
    parser.add_argument(
        "--allow-tool",
        action="append",
        dest="allowed_tools",
        help="Specific tool name to allow. Repeatable.",
    )
    parser.add_argument(
        "--allow-path",
        action="append",
        dest="allowed_paths",
        help="Approved filesystem path for path-locked leases. Repeatable.",
    )
    parser.add_argument(
        "--intent-action",
        action="append",
        dest="intent_actions",
        help="Approved Android intent action for intent-locked leases. Repeatable.",
    )
    parser.add_argument(
        "--intent-package",
        action="append",
        dest="intent_packages",
        help="Approved Android package for intent-locked leases. Repeatable.",
    )
    parser.add_argument(
        "--browser-package",
        action="append",
        dest="browser_packages",
        help="Approved browser package label like brave or chrome. Repeatable.",
    )
    parser.add_argument(
        "--constraint-notes",
        default="",
        help="Human note preserved inside lease constraints.",
    )
    parser.add_argument(
        "--max-uses",
        type=int,
        default=1,
        help="Single lease use budget (default: 1).",
    )
    parser.add_argument(
        "--max-tool-calls",
        type=int,
        default=None,
        help="Optional maximum successful tool calls before the lease self-destructs.",
    )
    parser.add_argument(
        "--max-shell-commands",
        type=int,
        default=None,
        help="Optional maximum shell.exec uses before the lease self-destructs.",
    )
    parser.add_argument(
        "--max-token-spend",
        type=int,
        default=None,
        help="Optional token-spend budget placeholder for future runtime accounting.",
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
                        principal_id=args.principal_id,
                        capabilities=args.capabilities,
                        allowed_tools=args.allowed_tools,
                        allowed_paths=args.allowed_paths,
                        intent_actions=args.intent_actions,
                        intent_packages=args.intent_packages,
                        browser_packages=args.browser_packages,
                        constraint_notes=args.constraint_notes,
                        lease_scope=args.lease_scope,
                        max_uses=args.max_uses,
                        max_tool_calls=args.max_tool_calls,
                        max_shell_commands=args.max_shell_commands,
                        max_token_spend=args.max_token_spend,
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
                        principal_id=args.principal_id,
                        capabilities=args.capabilities,
                        allowed_tools=args.allowed_tools,
                        allowed_paths=args.allowed_paths,
                        intent_actions=args.intent_actions,
                        intent_packages=args.intent_packages,
                        browser_packages=args.browser_packages,
                        constraint_notes=args.constraint_notes,
                        lease_scope=args.lease_scope,
                        max_uses=args.max_uses,
                        max_tool_calls=args.max_tool_calls,
                        max_shell_commands=args.max_shell_commands,
                        max_token_spend=args.max_token_spend,
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
