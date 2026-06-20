#!/usr/bin/env python3
"""Minimal human-review gate for the eyes worker lane."""

from __future__ import annotations

import datetime as dt
import json
import shlex
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = REPO_ROOT / "contracts" / "v1"
DEFAULT_ROOT = Path.home() / ".project_os" / "eyes"


@dataclass(frozen=True)
class ReviewPaths:
    root: Path
    review_dir: Path
    review_pending: Path
    latest_review: Path


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def resolve_paths(root: str | Path | None = None) -> ReviewPaths:
    base = Path(root).expanduser().resolve() if root else DEFAULT_ROOT
    review_dir = base / "review"
    return ReviewPaths(
        root=base,
        review_dir=review_dir,
        review_pending=review_dir / "pending",
        latest_review=review_dir / "review_required.json",
    )


def ensure_layout(root: str | Path | None = None) -> ReviewPaths:
    paths = resolve_paths(root)
    for path in (paths.root, paths.review_dir, paths.review_pending):
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((CONTRACTS_DIR / name).read_text())


def _validate(payload: dict[str, Any], schema_name: str) -> None:
    jsonschema.validate(payload, _load_schema(schema_name))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


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
