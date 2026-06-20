from __future__ import annotations

import importlib.util
import pathlib
import sys

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


def test_android_eyes_worker_run_once_scans_and_processes(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "bill_note.txt").write_text("Invoice amount is $42.00 and due Monday.")

    result = android_eyes_worker_tooling.android_eyes_worker_run_once(
        root=str(tmp_path),
        max_items=1,
        scan_first=True,
    )

    assert result["success"] is True
    status = android_eyes_worker_tooling.android_eyes_worker_status(root=str(tmp_path))
    assert status["success"] is True
    assert status["status"]["queue_completed"] == 1
    assert status["status"]["results"] == 1


def test_android_eyes_worker_schedule_dry_run_creates_wrapper(tmp_path):
    result = android_eyes_worker_tooling.android_eyes_worker_schedule(
        root=str(tmp_path),
        job_id=4242,
        period_ms=900000,
        max_items=2,
        scan_first=False,
        dry_run=True,
    )

    assert result["success"] is True
    assert result["dry_run"] is True
    wrapper_path = pathlib.Path(result["wrapper"]["wrapper_path"])
    assert wrapper_path.is_file()
    wrapper_text = wrapper_path.read_text()
    assert "eyes_tick.py" in wrapper_text
    assert "--skip-scan" in wrapper_text
    assert "--job-id" in result["command"]


def test_android_eyes_worker_cancel_job_dry_run():
    result = android_eyes_worker_tooling.android_eyes_worker_cancel_job(
        job_id=4242,
        dry_run=True,
    )

    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["command"][1] == "--cancel"
