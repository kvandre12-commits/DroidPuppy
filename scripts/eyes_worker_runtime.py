from __future__ import annotations

import datetime as dt
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = REPO_ROOT / "contracts" / "v1"
DEFAULT_ROOT = Path.home() / ".project_os" / "eyes"


@dataclass(frozen=True)
class RuntimePaths:
    root: Path
    journal_dir: Path
    events_dir: Path
    runs_dir: Path
    runs_active: Path
    runs_completed: Path
    runs_failed: Path
    runs_recovered: Path
    latest_checkpoint: Path


@dataclass
class RunHandle:
    paths: RuntimePaths
    checkpoint_path: Path
    checkpoint: dict[str, Any]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((CONTRACTS_DIR / name).read_text())


def _validate(payload: dict[str, Any], schema_name: str) -> None:
    jsonschema.validate(payload, _load_schema(schema_name))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def resolve_paths(root: str | Path | None = None) -> RuntimePaths:
    base = Path(root).expanduser().resolve() if root else DEFAULT_ROOT
    journal_dir = base / "journal"
    runs_dir = journal_dir / "runs"
    return RuntimePaths(
        root=base,
        journal_dir=journal_dir,
        events_dir=journal_dir / "events",
        runs_dir=runs_dir,
        runs_active=runs_dir / "active",
        runs_completed=runs_dir / "completed",
        runs_failed=runs_dir / "failed",
        runs_recovered=runs_dir / "recovered",
        latest_checkpoint=runs_dir / "latest.json",
    )


def ensure_layout(root: str | Path | None = None) -> RuntimePaths:
    paths = resolve_paths(root)
    for path in (
        paths.root,
        paths.journal_dir,
        paths.events_dir,
        paths.runs_dir,
        paths.runs_active,
        paths.runs_completed,
        paths.runs_failed,
        paths.runs_recovered,
    ):
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _write_latest_checkpoint(paths: RuntimePaths, payload: dict[str, Any]) -> None:
    write_json(paths.latest_checkpoint, payload)


def _persist(handle: RunHandle) -> None:
    handle.checkpoint["updated_at"] = now_iso()
    _validate(handle.checkpoint, "eyes_worker_checkpoint.schema.json")
    write_json(handle.checkpoint_path, handle.checkpoint)
    _write_latest_checkpoint(handle.paths, handle.checkpoint)


def append_event(
    paths: RuntimePaths,
    *,
    run_id: str,
    worker_name: str,
    event_type: str,
    queue_item_id: str | None = None,
    artifact_id: str | None = None,
    result_ref: str | None = None,
    review_ref: str | None = None,
    details: dict[str, Any] | None = None,
) -> Path:
    event = {
        "contract_version": "1.0.0",
        "event_id": uid("eyes-event"),
        "run_id": run_id,
        "worker_name": worker_name,
        "event_type": event_type,
        "created_at": now_iso(),
        "queue_item_id": queue_item_id,
        "artifact_id": artifact_id,
        "result_ref": result_ref,
        "review_ref": review_ref,
        "details": details or {},
    }
    _validate(event, "eyes_worker_run_event.schema.json")
    event_path = (
        paths.events_dir
        / f"{event['created_at'].replace(':', '-')}_{event['event_id']}.json"
    )
    write_json(event_path, event)
    return event_path


def begin_run(
    root: str | Path | None,
    *,
    worker_name: str,
    max_items: int,
) -> RunHandle:
    paths = ensure_layout(root)
    checkpoint = {
        "contract_version": "1.0.0",
        "run_id": uid("eyes-run"),
        "worker_name": worker_name,
        "status": "running",
        "started_at": now_iso(),
        "updated_at": now_iso(),
        "completed_at": None,
        "max_items": max_items,
        "processed": 0,
        "completed": 0,
        "failed": 0,
        "current_queue_item_id": None,
        "current_claim_ref": None,
        "current_phase": None,
        "current_result_ref": None,
        "current_review_ref": None,
        "last_error": None,
        "result_refs": [],
        "review_refs": [],
    }
    checkpoint_path = paths.runs_active / f"{checkpoint['run_id']}.json"
    handle = RunHandle(
        paths=paths, checkpoint_path=checkpoint_path, checkpoint=checkpoint
    )
    _persist(handle)
    append_event(
        paths,
        run_id=str(checkpoint["run_id"]),
        worker_name=worker_name,
        event_type="run_started",
        details={"max_items": max_items},
    )
    return handle


def record_claim(
    handle: RunHandle,
    payload: dict[str, Any],
    *,
    claimed_path: Path,
) -> None:
    handle.checkpoint["processed"] = int(handle.checkpoint["processed"]) + 1
    handle.checkpoint["current_queue_item_id"] = str(payload["queue_item_id"])
    handle.checkpoint["current_claim_ref"] = str(claimed_path)
    handle.checkpoint["current_phase"] = "claimed"
    handle.checkpoint["current_result_ref"] = None
    handle.checkpoint["current_review_ref"] = None
    handle.checkpoint["last_error"] = None
    _persist(handle)
    append_event(
        handle.paths,
        run_id=str(handle.checkpoint["run_id"]),
        worker_name=str(handle.checkpoint["worker_name"]),
        event_type="item_claimed",
        queue_item_id=str(payload["queue_item_id"]),
        artifact_id=str(payload["artifact_id"]),
        details={"claimed_path": str(claimed_path)},
    )


def record_result_written(
    handle: RunHandle,
    payload: dict[str, Any],
    *,
    result_ref: str,
) -> None:
    handle.checkpoint["current_phase"] = "result_written"
    handle.checkpoint["current_result_ref"] = result_ref
    handle.checkpoint["result_refs"].append(result_ref)
    _persist(handle)
    append_event(
        handle.paths,
        run_id=str(handle.checkpoint["run_id"]),
        worker_name=str(handle.checkpoint["worker_name"]),
        event_type="result_written",
        queue_item_id=str(payload["queue_item_id"]),
        artifact_id=str(payload["artifact_id"]),
        result_ref=result_ref,
    )


def record_review_required(
    handle: RunHandle,
    payload: dict[str, Any],
    *,
    review_ref: str,
) -> None:
    handle.checkpoint["current_phase"] = "review_required"
    handle.checkpoint["current_review_ref"] = review_ref
    handle.checkpoint["review_refs"].append(review_ref)
    _persist(handle)
    append_event(
        handle.paths,
        run_id=str(handle.checkpoint["run_id"]),
        worker_name=str(handle.checkpoint["worker_name"]),
        event_type="review_required",
        queue_item_id=str(payload["queue_item_id"]),
        artifact_id=str(payload["artifact_id"]),
        result_ref=str(handle.checkpoint.get("current_result_ref") or "") or None,
        review_ref=review_ref,
    )


def record_item_completed(
    handle: RunHandle,
    payload: dict[str, Any],
    *,
    result_ref: str,
    review_ref: str | None = None,
) -> None:
    handle.checkpoint["completed"] = int(handle.checkpoint["completed"]) + 1
    handle.checkpoint["current_phase"] = None
    handle.checkpoint["current_queue_item_id"] = None
    handle.checkpoint["current_claim_ref"] = None
    handle.checkpoint["current_result_ref"] = None
    handle.checkpoint["current_review_ref"] = None
    handle.checkpoint["last_error"] = None
    _persist(handle)
    append_event(
        handle.paths,
        run_id=str(handle.checkpoint["run_id"]),
        worker_name=str(handle.checkpoint["worker_name"]),
        event_type="item_completed",
        queue_item_id=str(payload["queue_item_id"]),
        artifact_id=str(payload["artifact_id"]),
        result_ref=result_ref,
        review_ref=review_ref,
    )


def record_item_failed(
    handle: RunHandle,
    payload: dict[str, Any],
    *,
    error_text: str,
) -> None:
    handle.checkpoint["failed"] = int(handle.checkpoint["failed"]) + 1
    handle.checkpoint["current_phase"] = "failed"
    handle.checkpoint["last_error"] = error_text
    _persist(handle)
    append_event(
        handle.paths,
        run_id=str(handle.checkpoint["run_id"]),
        worker_name=str(handle.checkpoint["worker_name"]),
        event_type="item_failed",
        queue_item_id=str(payload["queue_item_id"]),
        artifact_id=str(payload["artifact_id"]),
        details={"error": error_text},
    )


def finalize_run(handle: RunHandle, *, status: str) -> Path:
    handle.checkpoint["status"] = status
    handle.checkpoint["completed_at"] = now_iso()
    handle.checkpoint["current_phase"] = None
    handle.checkpoint["current_queue_item_id"] = None
    handle.checkpoint["current_claim_ref"] = None
    handle.checkpoint["current_result_ref"] = None
    handle.checkpoint["current_review_ref"] = None
    _persist(handle)
    destination_dir = {
        "completed": handle.paths.runs_completed,
        "failed": handle.paths.runs_failed,
        "recovered": handle.paths.runs_recovered,
    }.get(status, handle.paths.runs_failed)
    destination = destination_dir / handle.checkpoint_path.name
    handle.checkpoint_path.replace(destination)
    handle.checkpoint_path = destination
    append_event(
        handle.paths,
        run_id=str(handle.checkpoint["run_id"]),
        worker_name=str(handle.checkpoint["worker_name"]),
        event_type=f"run_{status}",
        details={
            "processed": handle.checkpoint["processed"],
            "completed": handle.checkpoint["completed"],
            "failed": handle.checkpoint["failed"],
        },
    )
    return destination


def load_active_runs(
    root: str | Path | None = None,
) -> list[tuple[Path, dict[str, Any]]]:
    paths = ensure_layout(root)
    runs: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(paths.runs_active.glob("*.json")):
        payload = read_json(path)
        _validate(payload, "eyes_worker_checkpoint.schema.json")
        runs.append((path, payload))
    return runs


def find_active_run(
    root: str | Path | None,
    run_id: str,
) -> tuple[RuntimePaths, Path | None, dict[str, Any] | None]:
    paths = ensure_layout(root)
    candidate = paths.runs_active / f"{run_id}.json"
    if not candidate.is_file():
        return paths, None, None
    payload = read_json(candidate)
    _validate(payload, "eyes_worker_checkpoint.schema.json")
    return paths, candidate, payload


def stale_age_seconds(timestamp: str | None) -> int | None:
    if not timestamp:
        return None
    try:
        created = dt.datetime.fromisoformat(timestamp)
    except ValueError:
        return None
    age = dt.datetime.now(dt.timezone.utc) - created.astimezone(dt.timezone.utc)
    return max(int(age.total_seconds()), 0)


def archive_recovered_run(
    root: str | Path | None,
    *,
    run_id: str,
    note: str,
) -> Path | None:
    paths, checkpoint_path, payload = find_active_run(root, run_id)
    if checkpoint_path is None or payload is None:
        return None
    handle = RunHandle(paths=paths, checkpoint_path=checkpoint_path, checkpoint=payload)
    handle.checkpoint["status"] = "recovered"
    handle.checkpoint["last_error"] = note
    handle.checkpoint["completed_at"] = now_iso()
    return finalize_run(handle, status="recovered")


def journal_snapshot(root: str | Path | None = None) -> dict[str, int | str]:
    paths = ensure_layout(root)
    active_runs = len(list(paths.runs_active.glob("*.json")))
    latest_run_id = ""
    latest_run_status = ""
    if paths.latest_checkpoint.exists():
        latest = read_json(paths.latest_checkpoint)
        latest_run_id = str(latest.get("run_id", ""))
        latest_run_status = str(latest.get("status", ""))
    return {
        "journal_events": len(list(paths.events_dir.glob("*.json"))),
        "active_runs": active_runs,
        "completed_runs": len(list(paths.runs_completed.glob("*.json"))),
        "failed_runs": len(list(paths.runs_failed.glob("*.json"))),
        "recovered_runs": len(list(paths.runs_recovered.glob("*.json"))),
        "latest_checkpoint": str(paths.latest_checkpoint)
        if paths.latest_checkpoint.exists()
        else "",
        "latest_run_id": latest_run_id,
        "latest_run_status": latest_run_status,
    }
