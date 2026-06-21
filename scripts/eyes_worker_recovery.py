from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema

import eyes_review_gate
import eyes_worker_runtime

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = REPO_ROOT / "contracts" / "v1"
DEFAULT_ROOT = Path.home() / ".project_os" / "eyes"


@dataclass(frozen=True)
class RecoverySummary:
    inspected: int
    requeued: int
    completed: int
    skipped: int
    recovered_run_ids: list[str]


def _root(root: str | Path | None = None) -> Path:
    return Path(root).expanduser().resolve() if root else DEFAULT_ROOT


def _queue_dir(root: str | Path | None, name: str) -> Path:
    path = _root(root) / "queue" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _results_dir(root: str | Path | None) -> Path:
    path = _root(root) / "results"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _review_root(root: str | Path | None) -> Path:
    path = _root(root) / "review"
    path.mkdir(parents=True, exist_ok=True)
    (path / "pending").mkdir(parents=True, exist_ok=True)
    return path


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((CONTRACTS_DIR / name).read_text())


def _validate(payload: dict[str, Any], schema_name: str) -> None:
    jsonschema.validate(payload, _load_schema(schema_name))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def stale_claims(
    root: str | Path | None = None,
    *,
    stale_after_seconds: int = 900,
) -> list[tuple[Path, dict[str, Any], int]]:
    items: list[tuple[Path, dict[str, Any], int]] = []
    for path in sorted(_queue_dir(root, "claimed").glob("*.json")):
        payload = _read_json(path)
        _validate(payload, "eyes_queue_item.schema.json")
        age_seconds = eyes_worker_runtime.stale_age_seconds(
            str(payload.get("claimed_at") or "")
        )
        if age_seconds is not None and age_seconds >= stale_after_seconds:
            items.append((path, payload, age_seconds))
    return items


def count_stale_claims(
    root: str | Path | None = None,
    *,
    stale_after_seconds: int = 900,
) -> int:
    return len(stale_claims(root, stale_after_seconds=stale_after_seconds))


def recover_stale_claims(
    root: str | Path | None = None,
    *,
    stale_after_seconds: int = 900,
    notify_reviews: bool = False,
    worker_name: str,
) -> RecoverySummary:
    if stale_after_seconds < 0:
        raise ValueError("stale_after_seconds must be at least 0")

    root_path = _root(root)
    queue_claimed = _queue_dir(root_path, "claimed")
    queue_pending = _queue_dir(root_path, "pending")
    queue_completed = _queue_dir(root_path, "completed")
    inspected = len(list(queue_claimed.glob("*.json")))
    requeued = completed = 0
    recovered_run_ids: list[str] = []

    for claimed_path, payload, age_seconds in stale_claims(
        root_path,
        stale_after_seconds=stale_after_seconds,
    ):
        run_id = str(payload.get("run_id") or "").strip()
        result_ref = str(payload.get("result_ref") or "").strip()
        review_ref = str(payload.get("review_ref") or "").strip()
        checkpoint_payload = None
        if run_id:
            _, _, checkpoint_payload = eyes_worker_runtime.find_active_run(
                root_path, run_id
            )
            if checkpoint_payload is not None:
                result_ref = (
                    result_ref
                    or str(checkpoint_payload.get("current_result_ref") or "").strip()
                )
                review_ref = (
                    review_ref
                    or str(checkpoint_payload.get("current_review_ref") or "").strip()
                )

        if result_ref and Path(result_ref).is_file():
            result = _read_json(Path(result_ref))
            _validate(result, "eyes_worker_result.schema.json")
            if result.get("requires_human_review") and not review_ref:
                _results_dir(root_path)
                _review_root(root_path)
                review_info = eyes_review_gate.emit_review_required(
                    result,
                    result_ref,
                    root=root_path,
                    notify=notify_reviews,
                )
                review_ref = str(review_info["review_ref"])
            payload["status"] = "completed"
            payload["completed_at"] = _now()
            payload["result_ref"] = result_ref
            payload["review_ref"] = review_ref or None
            payload["last_error"] = None
            _validate(payload, "eyes_queue_item.schema.json")
            destination = queue_completed / claimed_path.name
            _write_json(destination, payload)
            claimed_path.unlink()
            completed += 1
            if run_id:
                eyes_worker_runtime.append_event(
                    eyes_worker_runtime.ensure_layout(root_path),
                    run_id=run_id,
                    worker_name=worker_name,
                    event_type="claim_completed",
                    queue_item_id=str(payload["queue_item_id"]),
                    artifact_id=str(payload["artifact_id"]),
                    result_ref=result_ref,
                    review_ref=review_ref or None,
                    details={"stale_age_seconds": age_seconds},
                )
                if run_id not in recovered_run_ids:
                    recovered_run_ids.append(run_id)
                eyes_worker_runtime.archive_recovered_run(
                    root_path,
                    run_id=run_id,
                    note=f"Recovered stale claimed item at age={age_seconds}s",
                )
            continue

        payload["status"] = "pending"
        payload["run_id"] = None
        payload["worker_name"] = None
        payload["claimed_at"] = None
        payload["completed_at"] = None
        payload["failed_at"] = None
        payload["result_ref"] = None
        payload["review_ref"] = None
        payload["last_error"] = (
            f"Recovered stale claim after {age_seconds}s at {_now()}"
        )
        _validate(payload, "eyes_queue_item.schema.json")
        destination = queue_pending / claimed_path.name
        _write_json(destination, payload)
        claimed_path.unlink()
        requeued += 1
        if run_id:
            eyes_worker_runtime.append_event(
                eyes_worker_runtime.ensure_layout(root_path),
                run_id=run_id,
                worker_name=worker_name,
                event_type="claim_requeued",
                queue_item_id=str(payload["queue_item_id"]),
                artifact_id=str(payload["artifact_id"]),
                details={"stale_age_seconds": age_seconds},
            )
            if run_id not in recovered_run_ids:
                recovered_run_ids.append(run_id)
            eyes_worker_runtime.archive_recovered_run(
                root_path,
                run_id=run_id,
                note=f"Requeued stale claimed item at age={age_seconds}s",
            )

    skipped = inspected - requeued - completed
    return RecoverySummary(
        inspected=inspected,
        requeued=requeued,
        completed=completed,
        skipped=skipped,
        recovered_run_ids=recovered_run_ids,
    )
