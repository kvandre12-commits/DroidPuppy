#!/usr/bin/env python3
"""Project OS eyes inbox: local evidence intake for manual snapshots and exports.

This is the first practical unlock for the "your eyes are not trapped in the
foreground" doctrine:

- human navigates hostile/mobile surfaces
- human drops files into a bounded inbox
- local intake creates validated manifests and routed queue items
- later workers can pick those up without re-fighting Android/app security
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import mimetypes
import re
import shutil
import uuid
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = REPO_ROOT / "contracts" / "v1"
DEFAULT_ROOT = Path.home() / ".project_os" / "eyes"
ROUTING_KEYWORDS = {
    "bill_review": ("bill", "invoice", "statement", "utility", "payment"),
    "school_digest": ("syllabus", "class", "course", "assignment", "deadline"),
    "compare_candidate": ("compare", "diff", "versus", "vs"),
}
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".log", ".json"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
HTML_EXTENSIONS = {".html", ".htm"}
PDF_EXTENSIONS = {".pdf"}
MAX_PREVIEW_CHARS = 1200


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
class IntakePaths:
    root: Path
    inbox: Path
    manifests: Path
    queue_pending: Path
    processed: Path
    failed: Path


@dataclass(frozen=True)
class ScanSummary:
    scanned: int
    ingested: int
    duplicates: int
    failed: int
    pending_queue_items: int


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def resolve_paths(root: str | Path | None = None) -> IntakePaths:
    base = Path(root).expanduser().resolve() if root else DEFAULT_ROOT
    return IntakePaths(
        root=base,
        inbox=base / "inbox",
        manifests=base / "manifests",
        queue_pending=base / "queue" / "pending",
        processed=base / "processed",
        failed=base / "failed",
    )


def ensure_layout(root: str | Path | None = None) -> IntakePaths:
    paths = resolve_paths(root)
    for path in (
        paths.root,
        paths.inbox,
        paths.manifests,
        paths.queue_pending,
        paths.processed,
        paths.failed,
    ):
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((CONTRACTS_DIR / name).read_text())


def _read_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _existing_hashes(manifests_dir: Path) -> set[str]:
    hashes: set[str] = set()
    for manifest_path in manifests_dir.glob("*.json"):
        try:
            hashes.add(str(_read_manifest(manifest_path).get("sha256", "")))
        except json.JSONDecodeError:
            continue
    return hashes


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in HTML_EXTENSIONS:
        return "html"
    if suffix in PDF_EXTENSIONS:
        return "pdf"
    if suffix in TEXT_EXTENSIONS:
        return "json" if suffix == ".json" else "text"
    return "unknown"


def _source_type(path: Path, artifact_kind: str) -> str:
    name = path.name.lower()
    if artifact_kind in {"image", "html", "pdf", "json"}:
        if "note" in name:
            return "manual_note"
        return "manual_snapshot" if artifact_kind == "image" else "manual_export"
    if artifact_kind == "text":
        return "manual_note"
    return "unknown"


def _normalize_text(value: str) -> str:
    compact = re.sub(r"\s+", " ", value or "").strip()
    return compact[:MAX_PREVIEW_CHARS]


def _extract_preview(path: Path, artifact_kind: str) -> str:
    if artifact_kind in {"text", "json"}:
        return _normalize_text(path.read_text(errors="replace"))
    if artifact_kind == "html":
        parser = _HTMLTextExtractor()
        parser.feed(path.read_text(errors="replace"))
        return _normalize_text(parser.get_text())
    if artifact_kind == "pdf":
        return "PDF captured; text extraction not yet implemented in this intake slice."
    if artifact_kind == "image":
        return "Image captured; route to OCR or human review."
    return ""


def _infer_routing(
    path: Path, artifact_kind: str, preview_text: str
) -> tuple[str, bool]:
    haystack = f"{path.name.lower()} {preview_text.lower()}"
    for route, keywords in ROUTING_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return route, route != "compare_candidate"
    if artifact_kind == "image":
        return "ocr_review", True
    if artifact_kind == "html":
        return "page_summary", False
    if artifact_kind == "pdf":
        return "document_digest", True
    if artifact_kind == "json":
        return "structured_review", False
    if artifact_kind == "text":
        return "text_summary", False
    return "manual_triage", True


def _priority_for_route(route: str) -> str:
    if route in {"bill_review", "school_digest"}:
        return "high"
    return "normal"


def _mime_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _validate(data: dict[str, Any], schema_name: str) -> None:
    jsonschema.validate(data, _load_schema(schema_name))


def _build_artifact(path: Path, stored_path: Path | None = None) -> dict[str, Any]:
    artifact_kind = _artifact_kind(path)
    preview_text = _extract_preview(path, artifact_kind)
    routing_hint, requires_human_review = _infer_routing(
        path, artifact_kind, preview_text
    )
    stat = path.stat()
    captured_at = dt.datetime.fromtimestamp(stat.st_mtime, dt.timezone.utc).isoformat()
    artifact = {
        "contract_version": "1.0.0",
        "artifact_id": _uid("eyes"),
        "source_type": _source_type(path, artifact_kind),
        "artifact_kind": artifact_kind,
        "captured_at": captured_at,
        "ingested_at": _now(),
        "original_path": str(path),
        "stored_path": str(stored_path) if stored_path else None,
        "sha256": _sha256(path),
        "bytes": stat.st_size,
        "mime_type": _mime_type(path),
        "labels": [],
        "preview_text": preview_text,
        "routing_hint": routing_hint,
        "requires_human_review": requires_human_review,
        "operator_notes": "",
    }
    _validate(artifact, "eyes_artifact.schema.json")
    return artifact


def _build_queue_item(artifact: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    queue_item = {
        "contract_version": "1.0.0",
        "queue_item_id": _uid("queue"),
        "artifact_id": artifact["artifact_id"],
        "worker_class": artifact["routing_hint"],
        "status": "pending",
        "priority": _priority_for_route(str(artifact["routing_hint"])),
        "reason": (
            f"Artifact kind '{artifact['artifact_kind']}' routed to "
            f"'{artifact['routing_hint']}'."
        ),
        "input_ref": str(manifest_path),
        "created_at": _now(),
        "attempts": 0,
        "worker_name": None,
        "claimed_at": None,
        "completed_at": None,
        "failed_at": None,
        "result_ref": None,
        "last_error": None,
    }
    _validate(queue_item, "eyes_queue_item.schema.json")
    return queue_item


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _move_to_processed(paths: IntakePaths, source_path: Path, artifact_id: str) -> Path:
    destination = paths.processed / f"{artifact_id}__{source_path.name}"
    shutil.move(str(source_path), str(destination))
    return destination


def scan_inbox(
    root: str | Path | None = None, *, move_files: bool = True
) -> ScanSummary:
    paths = ensure_layout(root)
    existing_hashes = _existing_hashes(paths.manifests)
    scanned = ingested = duplicates = failed = 0

    for item in sorted(paths.inbox.iterdir()):
        if not item.is_file():
            continue
        scanned += 1
        try:
            digest = _sha256(item)
            if digest in existing_hashes:
                duplicates += 1
                target = paths.failed / f"duplicate__{item.name}"
                if move_files:
                    shutil.move(str(item), str(target))
                continue

            artifact = _build_artifact(item)
            stored_path = None
            if move_files:
                stored_path = _move_to_processed(paths, item, artifact["artifact_id"])
                artifact["stored_path"] = str(stored_path)
                _validate(artifact, "eyes_artifact.schema.json")

            manifest_path = paths.manifests / f"{artifact['artifact_id']}.json"
            queue_item = _build_queue_item(artifact, manifest_path)
            queue_path = paths.queue_pending / f"{queue_item['queue_item_id']}.json"

            _write_json(manifest_path, artifact)
            _write_json(queue_path, queue_item)
            existing_hashes.add(str(artifact["sha256"]))
            ingested += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            error_record = {
                "file": str(item),
                "error": repr(exc),
                "ts": _now(),
            }
            _write_json(paths.failed / f"failed__{item.stem}.json", error_record)
    pending_queue_items = len(list(paths.queue_pending.glob("*.json")))
    return ScanSummary(
        scanned=scanned,
        ingested=ingested,
        duplicates=duplicates,
        failed=failed,
        pending_queue_items=pending_queue_items,
    )


def status_snapshot(root: str | Path | None = None) -> dict[str, int | str]:
    paths = ensure_layout(root)
    return {
        "root": str(paths.root),
        "inbox_files": len([p for p in paths.inbox.iterdir() if p.is_file()]),
        "manifests": len(list(paths.manifests.glob("*.json"))),
        "pending_queue_items": len(list(paths.queue_pending.glob("*.json"))),
        "processed_files": len([p for p in paths.processed.iterdir() if p.is_file()]),
        "failed_records": len(list(paths.failed.glob("*.json"))),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project OS eyes inbox intake worker")
    parser.add_argument(
        "--root",
        help="Override the eyes inbox root directory (default: ~/.project_os/eyes).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Create the eyes inbox directory layout.")

    scan_parser = subparsers.add_parser(
        "scan", help="Ingest inbox files into manifests and pending queue items."
    )
    scan_parser.add_argument(
        "--no-move",
        action="store_true",
        help="Leave source files in inbox instead of moving them to processed/failed.",
    )

    subparsers.add_parser("status", help="Show eyes inbox counts.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        paths = ensure_layout(args.root)
        print(f"Initialized eyes inbox at {paths.root}")
        return 0

    if args.command == "scan":
        summary = scan_inbox(args.root, move_files=not args.no_move)
        print(
            "Scanned {scanned} file(s): ingested={ingested}, duplicates={duplicates}, "
            "failed={failed}, pending_queue_items={pending}".format(
                scanned=summary.scanned,
                ingested=summary.ingested,
                duplicates=summary.duplicates,
                failed=summary.failed,
                pending=summary.pending_queue_items,
            )
        )
        return 0

    if args.command == "status":
        snapshot = status_snapshot(args.root)
        print(json.dumps(snapshot, indent=2, sort_keys=True))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
