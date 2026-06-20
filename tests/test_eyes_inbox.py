from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import jsonschema

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "eyes_inbox.py"
SPEC = importlib.util.spec_from_file_location("eyes_inbox", MODULE_PATH)
eyes_inbox = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = eyes_inbox
SPEC.loader.exec_module(eyes_inbox)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACTS_DIR = REPO_ROOT / "contracts" / "v1"


def _load_schema(name: str) -> dict:
    return json.loads((CONTRACTS_DIR / name).read_text())


def test_ensure_layout_creates_expected_directories(tmp_path):
    paths = eyes_inbox.ensure_layout(tmp_path)

    assert paths.inbox.is_dir()
    assert paths.manifests.is_dir()
    assert paths.queue_pending.is_dir()
    assert paths.processed.is_dir()
    assert paths.failed.is_dir()


def test_scan_inbox_creates_valid_manifest_and_queue_item(tmp_path):
    paths = eyes_inbox.ensure_layout(tmp_path)
    dropped = paths.inbox / "course_deadline_note.txt"
    dropped.write_text("Assignment deadline moved to Friday.")

    summary = eyes_inbox.scan_inbox(tmp_path)

    assert summary.scanned == 1
    assert summary.ingested == 1
    manifest_path = next(paths.manifests.glob("*.json"))
    queue_path = next(paths.queue_pending.glob("*.json"))

    manifest = json.loads(manifest_path.read_text())
    queue_item = json.loads(queue_path.read_text())

    jsonschema.validate(manifest, _load_schema("eyes_artifact.schema.json"))
    jsonschema.validate(queue_item, _load_schema("eyes_queue_item.schema.json"))

    assert manifest["routing_hint"] == "school_digest"
    assert queue_item["worker_class"] == "school_digest"
    assert len(list(paths.processed.iterdir())) == 1


def test_scan_inbox_flags_image_for_human_review(tmp_path):
    paths = eyes_inbox.ensure_layout(tmp_path)
    dropped = paths.inbox / "weird_site.png"
    dropped.write_bytes(b"not really an image but good enough for intake")

    eyes_inbox.scan_inbox(tmp_path)
    manifest = json.loads(next(paths.manifests.glob("*.json")).read_text())

    assert manifest["artifact_kind"] == "image"
    assert manifest["routing_hint"] == "ocr_review"
    assert manifest["requires_human_review"] is True


def test_scan_inbox_skips_duplicate_content(tmp_path):
    paths = eyes_inbox.ensure_layout(tmp_path)
    (paths.inbox / "first.txt").write_text("same content")
    eyes_inbox.scan_inbox(tmp_path)

    (paths.inbox / "second.txt").write_text("same content")
    summary = eyes_inbox.scan_inbox(tmp_path)

    assert summary.duplicates == 1
    assert len(list(paths.manifests.glob("*.json"))) == 1
    assert any(path.name.startswith("duplicate__") for path in paths.failed.iterdir())


def test_status_snapshot_reports_counts(tmp_path):
    paths = eyes_inbox.ensure_layout(tmp_path)
    (paths.inbox / "bill_statement.txt").write_text("Utility bill increased by 15%.")
    eyes_inbox.scan_inbox(tmp_path)

    status = eyes_inbox.status_snapshot(tmp_path)

    assert status["inbox_files"] == 0
    assert status["manifests"] == 1
    assert status["pending_queue_items"] == 1
    assert status["processed_files"] == 1
