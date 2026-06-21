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
eyes_worker_runtime = _load_module(
    "eyes_worker_runtime", SCRIPTS_DIR / "eyes_worker_runtime.py"
)
eyes_tick = _load_module("eyes_tick", SCRIPTS_DIR / "eyes_tick.py")


def test_run_batch_creates_result_and_completes_queue_item(tmp_path):
    paths = eyes_inbox.ensure_layout(tmp_path)
    (paths.inbox / "utility_bill.txt").write_text(
        "Utility bill total is $19.99 and due Friday."
    )
    eyes_inbox.scan_inbox(tmp_path)

    summary = eyes_queue_worker.run_batch(tmp_path, max_items=1, notify_reviews=False)

    assert summary.processed == 1
    assert summary.completed == 1
    assert len(summary.result_refs) == 1
    result = json.loads(pathlib.Path(summary.result_refs[0]).read_text())
    assert result["worker_class"] == "bill_review"
    assert result["status"] == "completed"
    assert "$19.99" in " ".join(result["extracted_facts"])
    assert len(summary.review_refs) == 1
    review = json.loads(pathlib.Path(summary.review_refs[0]).read_text())
    assert review["title"].startswith("Review Required: ")
    assert review["body"].startswith("Artifact Ready")
    assert (tmp_path / "review" / "review_required.json").is_file()
    assert len(list((tmp_path / "queue" / "completed").glob("*.json"))) == 1


def test_run_batch_prefers_high_priority_queue_items(tmp_path):
    paths = eyes_inbox.ensure_layout(tmp_path)
    (paths.inbox / "plain_note.txt").write_text("just a normal note")
    (paths.inbox / "school_deadline.txt").write_text("assignment deadline tomorrow")
    eyes_inbox.scan_inbox(tmp_path)

    summary = eyes_queue_worker.run_batch(tmp_path, max_items=1, notify_reviews=False)

    result = json.loads(pathlib.Path(summary.result_refs[0]).read_text())
    assert result["worker_class"] == "school_digest"
    assert len(list((tmp_path / "queue" / "pending").glob("*.json"))) == 1


def test_run_batch_writes_runtime_journal(tmp_path):
    paths = eyes_inbox.ensure_layout(tmp_path)
    (paths.inbox / "utility_bill.txt").write_text(
        "Utility bill total is $19.99 and due Friday."
    )
    eyes_inbox.scan_inbox(tmp_path)

    summary = eyes_queue_worker.run_batch(tmp_path, max_items=1, notify_reviews=False)

    status = eyes_queue_worker.status_snapshot(tmp_path)
    checkpoint_path = (
        tmp_path / "journal" / "runs" / "completed" / f"{summary.run_id}.json"
    )
    checkpoint = json.loads(checkpoint_path.read_text())
    assert summary.run_id.startswith("eyes-run-")
    assert status["active_runs"] == 0
    assert status["completed_runs"] == 1
    assert status["journal_events"] >= 5
    assert checkpoint["processed"] == 1
    assert checkpoint["completed"] == 1


def test_recover_stale_claim_requeues_without_result(tmp_path):
    eyes_inbox_paths = eyes_inbox.ensure_layout(tmp_path)
    worker_paths = eyes_queue_worker.ensure_layout(tmp_path)
    (eyes_inbox_paths.inbox / "plain_note.txt").write_text("just a normal note")
    eyes_inbox.scan_inbox(tmp_path)

    pending_path, payload = eyes_queue_worker._pending_items(worker_paths)[0]
    run_handle = eyes_worker_runtime.begin_run(
        tmp_path,
        worker_name=eyes_queue_worker.WORKER_NAME,
        max_items=1,
    )
    claimed_path, claimed_payload = eyes_queue_worker._claim_item(
        worker_paths,
        pending_path,
        payload,
        run_id=run_handle.checkpoint["run_id"],
    )
    eyes_worker_runtime.record_claim(
        run_handle,
        claimed_payload,
        claimed_path=claimed_path,
    )

    summary = eyes_queue_worker.recover_stale_claims(
        tmp_path,
        stale_after_seconds=0,
        notify_reviews=False,
    )

    status = eyes_queue_worker.status_snapshot(tmp_path)
    assert summary.requeued == 1
    assert summary.completed == 0
    assert status["queue_pending"] == 1
    assert status["queue_claimed"] == 0
    assert status["recovered_runs"] == 1


def test_recover_stale_claim_completes_when_result_exists(tmp_path):
    eyes_inbox_paths = eyes_inbox.ensure_layout(tmp_path)
    worker_paths = eyes_queue_worker.ensure_layout(tmp_path)
    (eyes_inbox_paths.inbox / "bill_note.txt").write_text(
        "Invoice amount is $42.00 and due Monday."
    )
    eyes_inbox.scan_inbox(tmp_path)

    pending_path, payload = eyes_queue_worker._pending_items(worker_paths)[0]
    run_handle = eyes_worker_runtime.begin_run(
        tmp_path,
        worker_name=eyes_queue_worker.WORKER_NAME,
        max_items=1,
    )
    claimed_path, claimed_payload = eyes_queue_worker._claim_item(
        worker_paths,
        pending_path,
        payload,
        run_id=run_handle.checkpoint["run_id"],
    )
    eyes_worker_runtime.record_claim(
        run_handle,
        claimed_payload,
        claimed_path=claimed_path,
    )
    manifest = eyes_queue_worker._read_json(
        eyes_queue_worker._manifest_path_for(claimed_payload)
    )
    result = eyes_queue_worker._build_result(claimed_payload, manifest)
    result_path = eyes_queue_worker._write_result(worker_paths, result)
    eyes_worker_runtime.record_result_written(
        run_handle,
        claimed_payload,
        result_ref=result_path,
    )

    summary = eyes_queue_worker.recover_stale_claims(
        tmp_path,
        stale_after_seconds=0,
        notify_reviews=False,
    )

    completed_files = list((tmp_path / "queue" / "completed").glob("*.json"))
    completed_payload = json.loads(completed_files[0].read_text())
    assert summary.completed == 1
    assert summary.requeued == 0
    assert completed_payload["result_ref"] == result_path
    assert completed_payload["review_ref"]
    assert (tmp_path / "review" / "review_required.json").is_file()


def test_eyes_tick_scans_and_processes_in_one_shot(tmp_path):
    paths = eyes_inbox.ensure_layout(tmp_path)
    (paths.inbox / "manual_page.txt").write_text(
        "This page says the task was approved."
    )

    exit_code = eyes_tick.main(
        ["--root", str(tmp_path), "--max-items", "1", "--no-notify"]
    )

    assert exit_code == 0
    status = eyes_queue_worker.status_snapshot(tmp_path)
    assert status["queue_completed"] == 1
    assert status["results"] == 1
    assert status["review_pending"] == 0
