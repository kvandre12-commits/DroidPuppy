from __future__ import annotations

import importlib.util
import pathlib
import sys

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "code_puppy"
    / "plugins"
    / "android_eyes_worker_kit"
    / "tooling.py"
)
SPEC = importlib.util.spec_from_file_location(
    "android_eyes_worker_tooling", MODULE_PATH
)
android_eyes_worker_tooling = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = android_eyes_worker_tooling
SPEC.loader.exec_module(android_eyes_worker_tooling)


def _load_script_module(name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / file_name)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


eyes_inbox = _load_script_module("eyes_inbox_for_worker_kit", "eyes_inbox.py")
eyes_queue_worker = _load_script_module(
    "eyes_queue_worker_for_worker_kit", "eyes_queue_worker.py"
)
eyes_worker_runtime = _load_script_module(
    "eyes_worker_runtime_for_worker_kit", "eyes_worker_runtime.py"
)


def test_android_eyes_worker_run_once_scans_and_processes(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "bill_note.txt").write_text("Invoice amount is $42.00 and due Monday.")

    result = android_eyes_worker_tooling.android_eyes_worker_run_once(
        root=str(tmp_path),
        max_items=1,
        scan_first=True,
        notify_reviews=False,
    )

    assert result["success"] is True
    status = android_eyes_worker_tooling.android_eyes_worker_status(root=str(tmp_path))
    assert status["success"] is True
    assert status["status"]["queue_completed"] == 1
    assert status["status"]["results"] == 1
    assert status["status"]["review_pending"] == 1


def test_android_eyes_worker_schedule_dry_run_creates_wrapper(tmp_path):
    result = android_eyes_worker_tooling.android_eyes_worker_schedule(
        root=str(tmp_path),
        job_id=4242,
        period_ms=900000,
        max_items=2,
        scan_first=False,
        notify_reviews=False,
        dry_run=True,
    )

    assert result["success"] is True
    assert result["dry_run"] is True
    wrapper_path = pathlib.Path(result["wrapper"]["wrapper_path"])
    assert wrapper_path.is_file()
    wrapper_text = wrapper_path.read_text()
    assert "eyes_tick.py" in wrapper_text
    assert "--skip-scan" in wrapper_text
    assert "--no-notify" in wrapper_text
    assert "--job-id" in result["command"]


def test_android_eyes_worker_recover_requeues_stale_claim(tmp_path):
    inbox_paths = eyes_inbox.ensure_layout(tmp_path)
    worker_paths = eyes_queue_worker.ensure_layout(tmp_path)
    (inbox_paths.inbox / "plain_note.txt").write_text("just a normal note")
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

    result = android_eyes_worker_tooling.android_eyes_worker_recover(
        root=str(tmp_path),
        stale_after_seconds=0,
        notify_reviews=False,
    )

    assert result["success"] is True
    assert result["recovery"]["requeued"] == 1


def test_android_eyes_worker_cancel_job_dry_run():
    result = android_eyes_worker_tooling.android_eyes_worker_cancel_job(
        job_id=4242,
        dry_run=True,
    )

    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["command"][1] == "--cancel"
