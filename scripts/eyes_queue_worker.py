#!/usr/bin/env python3
"""One-shot local worker for Project OS eyes inbox queue items.

This is the first "dancer" in the headless orchestration lane:
- pick one or more pending queue items
- perform a bounded deterministic transformation
- write a typed result artifact
- move the queue item to completed or failed
- exit immediately
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import uuid
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import jsonschema

import eyes_review_gate
import eyes_worker_recovery
import eyes_worker_runtime

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = REPO_ROOT / "contracts" / "v1"
DEFAULT_ROOT = Path.home() / ".project_os" / "eyes"
WORKER_NAME = "eyes_queue_worker.v1"
_PRIORITY_ORDER = {"high": 0, "normal": 1, "low": 2}
_TEXTUAL_EXTENSIONS = {".txt", ".md", ".csv", ".log", ".json", ".html", ".htm"}
_MAX_SUMMARY = 280


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def get_text(self) -> str:
        return " ".join(self.parts)


@dataclass(frozen=True)
class WorkerPaths:
    root: Path
    manifests: Path
    queue_pending: Path
    queue_claimed: Path
    queue_completed: Path
    queue_failed: Path
    results: Path
    review_dir: Path
    review_pending: Path
    latest_review: Path
    processed: Path
    failed: Path


@dataclass(frozen=True)
class WorkerRunSummary:
    processed: int
    completed: int
    failed: int
    idle: bool
    result_refs: list[str]
    review_refs: list[str]
    run_id: str


RecoverySummary = eyes_worker_recovery.RecoverySummary


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def resolve_paths(root: str | Path | None = None) -> WorkerPaths:
    base = Path(root).expanduser().resolve() if root else DEFAULT_ROOT
    return WorkerPaths(
        root=base,
        manifests=base / "manifests",
        queue_pending=base / "queue" / "pending",
        queue_claimed=base / "queue" / "claimed",
        queue_completed=base / "queue" / "completed",
        queue_failed=base / "queue" / "failed",
        results=base / "results",
        review_dir=base / "review",
        review_pending=(base / "review" / "pending"),
        latest_review=(base / "review" / "review_required.json"),
        processed=base / "processed",
        failed=base / "failed",
    )


def ensure_layout(root: str | Path | None = None) -> WorkerPaths:
    paths = resolve_paths(root)
    for path in (
        paths.root,
        paths.manifests,
        paths.queue_pending,
        paths.queue_claimed,
        paths.queue_completed,
        paths.queue_failed,
        paths.results,
        paths.review_dir,
        paths.review_pending,
        paths.processed,
        paths.failed,
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


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _shorten(value: str, limit: int = _MAX_SUMMARY) -> str:
    compact = _normalize_text(value)
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _manifest_path_for(queue_item: dict[str, Any]) -> Path:
    return Path(str(queue_item["input_ref"]))


def _artifact_text(manifest: dict[str, Any]) -> str:
    stored_path = manifest.get("stored_path") or manifest.get("original_path")
    if stored_path:
        candidate = Path(str(stored_path))
        if candidate.is_file() and candidate.suffix.lower() in _TEXTUAL_EXTENSIONS:
            text = candidate.read_text(errors="replace")
            if candidate.suffix.lower() in {".html", ".htm"}:
                parser = _HTMLTextExtractor()
                parser.feed(text)
                return _normalize_text(parser.get_text())
            return _normalize_text(text)
    return _normalize_text(str(manifest.get("preview_text", "")))


def _split_facts(text: str, *, max_facts: int = 3) -> list[str]:
    chunks = [
        chunk.strip(" -•\t") for chunk in re.split(r"[\n\.\?!]+", text) if chunk.strip()
    ]
    return [_shorten(chunk, limit=120) for chunk in chunks[:max_facts]]


def _currency_facts(text: str) -> list[str]:
    matches = re.findall(r"\$\s?\d+(?:,\d{3})*(?:\.\d{2})?", text)
    return matches[:3]


def _build_result(
    queue_item: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    worker_class = str(queue_item["worker_class"])
    text = _artifact_text(manifest)
    preview = text or str(manifest.get("preview_text", ""))
    facts = _split_facts(preview)
    requires_human_review = bool(manifest.get("requires_human_review", False))
    next_action = "Review in queue."

    if worker_class == "bill_review":
        money = _currency_facts(preview)
        facts = money + [fact for fact in facts if fact not in money]
        summary = _shorten(preview or "Billing artifact requires review.")
        next_action = (
            "Check due amount, due date, and whether a payment action is needed."
        )
        requires_human_review = True
    elif worker_class == "school_digest":
        summary = _shorten(preview or "School-related artifact captured.")
        next_action = (
            "Verify deadlines, tasks, and any follow-up messages or submissions."
        )
    elif worker_class == "page_summary":
        summary = _shorten(
            preview or "Page text captured from a manually reached surface."
        )
        next_action = (
            "Review summary and decide whether to preserve, compare, or escalate."
        )
    elif worker_class == "document_digest":
        summary = _shorten(
            preview or "Document captured; likely needs manual digestion."
        )
        next_action = "Open the document and perform a manual or OCR-assisted review."
        requires_human_review = True
    elif worker_class == "structured_review":
        summary = _shorten(preview or "Structured artifact captured for inspection.")
        next_action = "Inspect the structured data and route it to the appropriate downstream task."
    elif worker_class == "compare_candidate":
        summary = _shorten(preview or "Artifact looks like a compare/diff candidate.")
        next_action = "Pair this with a sibling artifact for compare/diff review."
        requires_human_review = True
    elif worker_class == "ocr_review":
        summary = "Image-like artifact captured; OCR or human review still required."
        facts = [
            str(manifest.get("stored_path") or manifest.get("original_path") or "")
        ]
        next_action = "Perform OCR or inspect the image manually."
        requires_human_review = True
    elif worker_class == "manual_triage":
        summary = _shorten(preview or "Artifact needs manual triage.")
        next_action = "Classify the artifact manually before delegating further work."
        requires_human_review = True
    else:
        summary = _shorten(preview or "Text artifact captured for later review.")
        next_action = (
            "Review the summary and decide whether further extraction is needed."
        )

    result = {
        "contract_version": "1.0.0",
        "result_id": _uid("eyes-result"),
        "queue_item_id": str(queue_item["queue_item_id"]),
        "artifact_id": str(queue_item["artifact_id"]),
        "worker_name": WORKER_NAME,
        "worker_class": worker_class,
        "status": "completed",
        "summary": summary,
        "extracted_facts": facts,
        "next_action": next_action,
        "requires_human_review": requires_human_review,
        "source_manifest": str(queue_item["input_ref"]),
        "source_artifact_path": manifest.get("stored_path")
        or manifest.get("original_path"),
        "created_at": _now(),
    }
    _validate(result, "eyes_worker_result.schema.json")
    return result


def _queue_sort_key(payload: dict[str, Any]) -> tuple[int, str, str]:
    priority = _PRIORITY_ORDER.get(str(payload.get("priority", "normal")), 99)
    created_at = str(payload.get("created_at", ""))
    queue_item_id = str(payload.get("queue_item_id", ""))
    return (priority, created_at, queue_item_id)


def _pending_items(paths: WorkerPaths) -> list[tuple[Path, dict[str, Any]]]:
    items: list[tuple[Path, dict[str, Any]]] = []
    for path in paths.queue_pending.glob("*.json"):
        payload = _read_json(path)
        _validate(payload, "eyes_queue_item.schema.json")
        items.append((path, payload))
    items.sort(key=lambda item: _queue_sort_key(item[1]))
    return items


def _claim_item(
    paths: WorkerPaths,
    path: Path,
    payload: dict[str, Any],
    *,
    run_id: str,
) -> tuple[Path, dict[str, Any]]:
    payload["status"] = "claimed"
    payload["run_id"] = run_id
    payload["worker_name"] = WORKER_NAME
    payload["claimed_at"] = _now()
    payload["attempts"] = int(payload.get("attempts", 0)) + 1
    payload["review_ref"] = None
    _validate(payload, "eyes_queue_item.schema.json")
    claimed_path = paths.queue_claimed / path.name
    _write_json(claimed_path, payload)
    path.unlink()
    return claimed_path, payload


def _write_result(paths: WorkerPaths, result: dict[str, Any]) -> str:
    result_path = paths.results / f"{result['result_id']}.json"
    _write_json(result_path, result)
    return str(result_path)


def _complete_item(
    paths: WorkerPaths,
    claimed_path: Path,
    payload: dict[str, Any],
    *,
    result_path: str,
) -> Path:
    payload["status"] = "completed"
    payload["completed_at"] = _now()
    payload["result_ref"] = result_path
    payload["last_error"] = None
    _validate(payload, "eyes_queue_item.schema.json")
    destination = paths.queue_completed / claimed_path.name
    _write_json(destination, payload)
    claimed_path.unlink()
    return destination


def _fail_item(
    paths: WorkerPaths, claimed_path: Path, payload: dict[str, Any], exc: Exception
) -> None:
    payload["status"] = "failed"
    payload["failed_at"] = _now()
    payload["last_error"] = repr(exc)
    _validate(payload, "eyes_queue_item.schema.json")
    destination = paths.queue_failed / claimed_path.name
    _write_json(destination, payload)
    claimed_path.unlink()


def _attach_review_ref(
    queue_path: Path, payload: dict[str, Any], review_ref: str
) -> dict[str, Any]:
    payload["review_ref"] = review_ref
    _validate(payload, "eyes_queue_item.schema.json")
    _write_json(queue_path, payload)
    return payload


def _stale_claims(paths: WorkerPaths, *, stale_after_seconds: int) -> int:
    return eyes_worker_recovery.count_stale_claims(
        paths.root,
        stale_after_seconds=stale_after_seconds,
    )


def recover_stale_claims(
    root: str | Path | None = None,
    *,
    stale_after_seconds: int = 900,
    notify_reviews: bool = False,
) -> RecoverySummary:
    return eyes_worker_recovery.recover_stale_claims(
        root,
        stale_after_seconds=stale_after_seconds,
        notify_reviews=notify_reviews,
        worker_name=WORKER_NAME,
    )


def run_batch(
    root: str | Path | None = None,
    *,
    max_items: int = 1,
    notify_reviews: bool = True,
) -> WorkerRunSummary:
    if max_items < 1:
        raise ValueError("max_items must be at least 1")
    paths = ensure_layout(root)
    run_handle = eyes_worker_runtime.begin_run(
        paths.root,
        worker_name=WORKER_NAME,
        max_items=max_items,
    )
    processed = completed = failed = 0
    result_refs: list[str] = []
    review_refs: list[str] = []

    for pending_path, payload in _pending_items(paths)[:max_items]:
        processed += 1
        claimed_path, claimed_payload = _claim_item(
            paths,
            pending_path,
            payload,
            run_id=str(run_handle.checkpoint["run_id"]),
        )
        eyes_worker_runtime.record_claim(
            run_handle,
            claimed_payload,
            claimed_path=claimed_path,
        )
        try:
            manifest = _read_json(_manifest_path_for(claimed_payload))
            _validate(manifest, "eyes_artifact.schema.json")
            result = _build_result(claimed_payload, manifest)
            result_path = _write_result(paths, result)
            eyes_worker_runtime.record_result_written(
                run_handle,
                claimed_payload,
                result_ref=result_path,
            )
            completed_queue_path = _complete_item(
                paths,
                claimed_path,
                claimed_payload,
                result_path=result_path,
            )
            result_refs.append(result_path)
            review_ref: str | None = None
            if result.get("requires_human_review"):
                review_info = eyes_review_gate.emit_review_required(
                    result,
                    result_path,
                    root=paths.root,
                    notify=notify_reviews,
                )
                review_ref = str(review_info["review_ref"])
                review_refs.append(review_ref)
                claimed_payload = _attach_review_ref(
                    completed_queue_path,
                    claimed_payload,
                    review_ref,
                )
                eyes_worker_runtime.record_review_required(
                    run_handle,
                    claimed_payload,
                    review_ref=review_ref,
                )
            completed += 1
            eyes_worker_runtime.record_item_completed(
                run_handle,
                claimed_payload,
                result_ref=result_path,
                review_ref=review_ref,
            )
        except Exception as exc:  # noqa: BLE001
            _fail_item(paths, claimed_path, claimed_payload, exc)
            failed += 1
            eyes_worker_runtime.record_item_failed(
                run_handle,
                claimed_payload,
                error_text=repr(exc),
            )

    eyes_worker_runtime.finalize_run(
        run_handle,
        status="completed" if failed == 0 else "failed",
    )
    return WorkerRunSummary(
        processed=processed,
        completed=completed,
        failed=failed,
        idle=processed == 0,
        result_refs=result_refs,
        review_refs=review_refs,
        run_id=str(run_handle.checkpoint["run_id"]),
    )


def status_snapshot(root: str | Path | None = None) -> dict[str, int | str]:
    paths = ensure_layout(root)
    snapshot: dict[str, int | str] = {
        "root": str(paths.root),
        "queue_pending": len(list(paths.queue_pending.glob("*.json"))),
        "queue_claimed": len(list(paths.queue_claimed.glob("*.json"))),
        "queue_completed": len(list(paths.queue_completed.glob("*.json"))),
        "queue_failed": len(list(paths.queue_failed.glob("*.json"))),
        "results": len(list(paths.results.glob("*.json"))),
        "review_pending": len(list(paths.review_pending.glob("*.json"))),
        "latest_review": str(paths.latest_review)
        if paths.latest_review.exists()
        else "",
        "stale_claims": _stale_claims(paths, stale_after_seconds=900),
    }
    snapshot.update(eyes_worker_runtime.journal_snapshot(paths.root))
    return snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project OS eyes queue worker")
    parser.add_argument(
        "--root",
        help="Override the eyes root directory (default: ~/.project_os/eyes).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init", help="Create the queue worker folder layout.")
    subparsers.add_parser("status", help="Show queue/result counts.")

    run_once = subparsers.add_parser("run-once", help="Process at most one queue item.")
    run_once.add_argument("--max-items", type=int, default=1)
    run_once.add_argument(
        "--no-notify",
        action="store_true",
        help="Create review-required artifacts without posting local notifications.",
    )

    run_batch_parser = subparsers.add_parser(
        "run-batch", help="Process up to max-items queue items and exit."
    )
    run_batch_parser.add_argument("--max-items", type=int, default=3)
    run_batch_parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Create review-required artifacts without posting local notifications.",
    )

    recover = subparsers.add_parser(
        "recover", help="Reconcile stale claimed queue items after a crash or kill."
    )
    recover.add_argument("--stale-after-seconds", type=int, default=900)
    recover.add_argument(
        "--no-notify",
        action="store_true",
        help="Do not post local notifications while recreating review artifacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        paths = ensure_layout(args.root)
        print(f"Initialized eyes queue worker at {paths.root}")
        return 0

    if args.command == "status":
        print(json.dumps(status_snapshot(args.root), indent=2, sort_keys=True))
        return 0

    if args.command in {"run-once", "run-batch"}:
        summary = run_batch(
            args.root,
            max_items=args.max_items,
            notify_reviews=not args.no_notify,
        )
        print(
            json.dumps(
                {
                    "run_id": summary.run_id,
                    "processed": summary.processed,
                    "completed": summary.completed,
                    "failed": summary.failed,
                    "idle": summary.idle,
                    "result_refs": summary.result_refs,
                    "review_refs": summary.review_refs,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "recover":
        summary = recover_stale_claims(
            args.root,
            stale_after_seconds=args.stale_after_seconds,
            notify_reviews=not args.no_notify,
        )
        print(
            json.dumps(
                {
                    "inspected": summary.inspected,
                    "requeued": summary.requeued,
                    "completed": summary.completed,
                    "skipped": summary.skipped,
                    "recovered_run_ids": summary.recovered_run_ids,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
