from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
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


eyes_review_gate = _load_module("eyes_review_gate", SCRIPTS_DIR / "eyes_review_gate.py")


def _fake_result() -> dict[str, str | bool]:
    return {
        "result_id": "eyes-result-123",
        "queue_item_id": "queue-123",
        "artifact_id": "trade_card_001",
        "worker_class": "bill_review",
        "next_action": "Operator must review before any execution.",
        "source_artifact_path": "/tmp/source.txt",
    }


def test_emit_review_required_writes_pending_and_latest(tmp_path):
    result = eyes_review_gate.emit_review_required(
        _fake_result(),
        tmp_path / "results" / "eyes-result-123.json",
        root=tmp_path,
        notify=False,
    )

    pending = json.loads(pathlib.Path(result["review_ref"]).read_text())
    latest = json.loads((tmp_path / "review" / "review_required.json").read_text())

    assert pending["artifact_id"] == "trade_card_001"
    assert pending["title"] == "Review Required: trade_card_001"
    assert pending["body"].startswith("Artifact Ready")
    assert latest["review_id"] == pending["review_id"]


def test_emit_review_required_posts_notification_when_available(tmp_path, monkeypatch):
    def fake_which(name: str) -> str | None:
        mapping = {
            "termux-notification": "/usr/bin/termux-notification",
            "termux-open": "/usr/bin/termux-open",
        }
        return mapping.get(name)

    def fake_run(args, capture_output, text, timeout, check):
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="ok", stderr=""
        )

    monkeypatch.setattr(eyes_review_gate.shutil, "which", fake_which)
    monkeypatch.setattr(eyes_review_gate.subprocess, "run", fake_run)

    result = eyes_review_gate.emit_review_required(
        _fake_result(),
        tmp_path / "results" / "eyes-result-123.json",
        root=tmp_path,
        notify=True,
    )

    notification = result["notification"]
    assert notification["success"] is True
    assert notification["command"][0] == "/usr/bin/termux-notification"
    assert "--action" in notification["command"]
    assert "/usr/bin/termux-open" in notification["tap_action"]
