from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "code_puppy"
    / "plugins"
    / "android_eyes_inbox_kit"
    / "tooling.py"
)
SPEC = importlib.util.spec_from_file_location("android_eyes_inbox_tooling", MODULE_PATH)
android_eyes_inbox_tooling = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = android_eyes_inbox_tooling
SPEC.loader.exec_module(android_eyes_inbox_tooling)


def test_android_eyes_inbox_init_and_status(tmp_path):
    init_result = android_eyes_inbox_tooling.android_eyes_inbox_init(root=str(tmp_path))
    status_result = android_eyes_inbox_tooling.android_eyes_inbox_status(
        root=str(tmp_path)
    )

    assert init_result["success"] is True
    assert pathlib.Path(init_result["created"]["inbox"]).is_dir()
    assert status_result["status"]["inbox_files"] == 0
    assert status_result["status"]["pending_queue_items"] == 0


def test_android_eyes_inbox_drop_text_and_url(tmp_path):
    android_eyes_inbox_tooling.android_eyes_inbox_init(root=str(tmp_path))

    text_result = android_eyes_inbox_tooling.android_eyes_inbox_drop_text(
        text="deadline moved to friday",
        root=str(tmp_path),
        name="school-note",
    )
    url_result = android_eyes_inbox_tooling.android_eyes_inbox_drop_url(
        url="https://example.com/weird",
        note="human reached this page manually",
        root=str(tmp_path),
        name="odd-page",
    )

    assert (
        pathlib.Path(text_result["file_path"]).read_text() == "deadline moved to friday"
    )
    assert (
        "human reached this page manually"
        in pathlib.Path(url_result["file_path"]).read_text()
    )

    status_result = android_eyes_inbox_tooling.android_eyes_inbox_status(
        root=str(tmp_path)
    )
    assert status_result["status"]["inbox_files"] == 2


def test_android_eyes_inbox_stage_file_copy_and_move(tmp_path):
    android_eyes_inbox_tooling.android_eyes_inbox_init(root=str(tmp_path))
    copy_source = tmp_path / "capture.txt"
    copy_source.write_text("copy me")
    move_source = tmp_path / "receipt.pdf"
    move_source.write_bytes(b"fake pdf")

    copy_result = android_eyes_inbox_tooling.android_eyes_inbox_stage_file(
        file_path=str(copy_source),
        root=str(tmp_path),
        move=False,
    )
    move_result = android_eyes_inbox_tooling.android_eyes_inbox_stage_file(
        file_path=str(move_source),
        root=str(tmp_path),
        move=True,
        name="receipt-upload.pdf",
    )

    assert pathlib.Path(copy_result["file_path"]).read_text() == "copy me"
    assert copy_source.exists()
    assert pathlib.Path(move_result["file_path"]).read_bytes() == b"fake pdf"
    assert not move_source.exists()


def test_android_eyes_inbox_drop_text_can_scan_now(tmp_path):
    result = android_eyes_inbox_tooling.android_eyes_inbox_drop_text(
        text="utility bill increased again",
        root=str(tmp_path),
        scan_now=True,
    )

    assert result["success"] is True
    assert result["scan_result"] is not None
    assert result["scan_result"]["success"] is True
    manifests_dir = pathlib.Path(tmp_path) / "manifests"
    queue_dir = pathlib.Path(tmp_path) / "queue" / "pending"
    manifest = json.loads(next(manifests_dir.glob("*.json")).read_text())

    assert manifest["routing_hint"] == "bill_review"
    assert len(list(queue_dir.glob("*.json"))) == 1


def test_android_eyes_inbox_doctor_reports_capabilities(tmp_path):
    doctor = android_eyes_inbox_tooling.android_eyes_inbox_doctor(root=str(tmp_path))

    assert doctor["success"] is True
    assert doctor["capabilities"]["drop_text"] is True
    assert doctor["capabilities"]["stage_file"] is True
