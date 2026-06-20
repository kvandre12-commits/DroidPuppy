from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


eyes_inbox = _load_module("eyes_inbox", SCRIPTS_DIR / "eyes_inbox.py")
eyes_queue_worker = _load_module(
    "eyes_queue_worker", SCRIPTS_DIR / "eyes_queue_worker.py"
)
eyes_tick = _load_module("eyes_tick", SCRIPTS_DIR / "eyes_tick.py")


def test_run_batch_creates_result_and_completes_queue_item(tmp_path):
    paths = eyes_inbox.ensure_layout(tmp_path)
    (paths.inbox / "utility_bill.txt").write_text(
        "Utility bill total is $19.99 and due Friday."
    )
    eyes_inbox.scan_inbox(tmp_path)

    summary = eyes_queue_worker.run_batch(tmp_path, max_items=1)

    assert summary.processed == 1
    assert summary.completed == 1
    assert len(summary.result_refs) == 1
    result = json.loads(pathlib.Path(summary.result_refs[0]).read_text())
    assert result["worker_class"] == "bill_review"
    assert result["status"] == "completed"
    assert "$19.99" in " ".join(result["extracted_facts"])
    assert len(list((tmp_path / "queue" / "completed").glob("*.json"))) == 1


def test_run_batch_prefers_high_priority_queue_items(tmp_path):
    paths = eyes_inbox.ensure_layout(tmp_path)
    (paths.inbox / "plain_note.txt").write_text("just a normal note")
    (paths.inbox / "school_deadline.txt").write_text("assignment deadline tomorrow")
    eyes_inbox.scan_inbox(tmp_path)

    summary = eyes_queue_worker.run_batch(tmp_path, max_items=1)

    result = json.loads(pathlib.Path(summary.result_refs[0]).read_text())
    assert result["worker_class"] == "school_digest"
    assert len(list((tmp_path / "queue" / "pending").glob("*.json"))) == 1


def test_eyes_tick_scans_and_processes_in_one_shot(tmp_path):
    paths = eyes_inbox.ensure_layout(tmp_path)
    (paths.inbox / "manual_page.txt").write_text(
        "This page says the task was approved."
    )

    exit_code = eyes_tick.main(["--root", str(tmp_path), "--max-items", "1"])

    assert exit_code == 0
    status = eyes_queue_worker.status_snapshot(tmp_path)
    assert status["queue_completed"] == 1
    assert status["results"] == 1
