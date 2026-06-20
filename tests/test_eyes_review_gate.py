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


def _emit_pending_review(tmp_path: pathlib.Path) -> tuple[dict, pathlib.Path]:
    result = eyes_review_gate.emit_review_required(
        _fake_result(),
        tmp_path / "results" / "eyes-result-123.json",
        root=tmp_path,
        notify=False,
    )
    review_path = pathlib.Path(result["review_ref"])
    return json.loads(review_path.read_text()), review_path


def test_emit_review_required_writes_pending_and_latest(tmp_path):
    pending, _ = _emit_pending_review(tmp_path)
    latest = json.loads((tmp_path / "review" / "review_required.json").read_text())

    assert pending["artifact_id"] == "trade_card_001"
    assert pending["title"] == "Review Required: trade_card_001"
    assert pending["body"].startswith("Artifact Ready")
    assert pending["status"] == "pending"
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


def test_approve_moves_review_mints_v2_lease_and_audit_events(tmp_path):
    pending, _ = _emit_pending_review(tmp_path)

    result = eyes_review_gate.decide_review(
        pending["review_id"],
        approve=True,
        root=tmp_path,
        decided_by="butcher",
        reason="Looks safe.",
        lease_minutes=10,
    )

    approved = json.loads(pathlib.Path(result["review_ref"]).read_text())
    decision_audit = json.loads(pathlib.Path(result["audit_event_ref"]).read_text())
    lease_audit = json.loads(pathlib.Path(result["lease_audit_event_ref"]).read_text())
    lease = json.loads(pathlib.Path(result["lease_ref"]).read_text())

    assert approved["status"] == "approved"
    assert approved["decided_by"] == "butcher"
    assert approved["decision_reason"] == "Looks safe."
    assert not any((tmp_path / "review" / "pending").glob("*.json"))

    assert decision_audit["event_type"] == "review_decision"
    assert decision_audit["details"]["decision"] == "APPROVED"
    assert decision_audit["details"]["review_artifact"]["status"] == "pending"

    assert lease_audit["event_type"] == "lease_minted"
    assert lease_audit["previous_event_sha256"] == decision_audit["event_sha256"]

    assert lease["contract_version"] == "2.0.0"
    assert lease["status"] == "active"
    assert lease["principal_id"] == eyes_review_gate.DEFAULT_PRINCIPAL_ID
    assert lease["capabilities"] == eyes_review_gate.DEFAULT_LEASE_CAPABILITIES
    assert lease["quotas"]["remaining_uses"] == 1
    assert lease["decision_event_ref"] == result["audit_event_ref"]
    assert lease["minted_event_ref"] == result["lease_audit_event_ref"]


def test_reject_moves_review_and_stamps_audit_without_lease(tmp_path):
    pending, _ = _emit_pending_review(tmp_path)

    result = eyes_review_gate.decide_review(
        pending["review_id"],
        approve=False,
        root=tmp_path,
        decided_by="butcher",
        reason="Nope.",
    )

    rejected = json.loads(pathlib.Path(result["review_ref"]).read_text())
    audit = json.loads(pathlib.Path(result["audit_event_ref"]).read_text())

    assert rejected["status"] == "rejected"
    assert rejected["lease_ref"] is None
    assert result["lease_ref"] is None
    assert result["lease_audit_event_ref"] is None
    assert audit["event_type"] == "review_decision"
    assert audit["details"]["decision"] == "REJECTED"
    assert not any((tmp_path / "leases" / "active").glob("*.json"))


def test_audit_events_form_hash_chain_across_decision_and_mint(tmp_path):
    first, _ = _emit_pending_review(tmp_path)
    eyes_review_gate.decide_review(first["review_id"], approve=True, root=tmp_path)

    second, _ = _emit_pending_review(tmp_path)
    result = eyes_review_gate.decide_review(
        second["review_id"], approve=False, root=tmp_path
    )

    audit_files = sorted((tmp_path / "audit" / "events").glob("*.json"))
    events = [json.loads(path.read_text()) for path in audit_files]
    assert len(events) == 3
    for previous, current in zip(events, events[1:]):
        assert current["previous_event_sha256"] == previous["event_sha256"]
    assert (
        json.loads(pathlib.Path(result["audit_event_ref"]).read_text())["event_id"]
        == events[-1]["event_id"]
    )


def test_custom_capability_lease_arguments_are_preserved(tmp_path):
    pending, _ = _emit_pending_review(tmp_path)

    result = eyes_review_gate.decide_review(
        pending["review_id"],
        approve=True,
        root=tmp_path,
        principal_id="worker-alpha",
        capabilities=["shell.exec"],
        allowed_tools=["agent_run_shell_command"],
        max_uses=2,
        max_tool_calls=2,
        max_shell_commands=1,
        max_token_spend=50000,
    )

    lease = json.loads(pathlib.Path(result["lease_ref"]).read_text())
    assert lease["principal_id"] == "worker-alpha"
    assert lease["capabilities"] == ["shell.exec"]
    assert lease["allowed_tools"] == ["agent_run_shell_command"]
    assert lease["quotas"]["max_uses"] == 2
    assert lease["quotas"]["max_tool_calls"] == 2
    assert lease["quotas"]["max_shell_commands"] == 1
    assert lease["quotas"]["max_token_spend"] == 50000


def test_main_approve_cli_returns_zero_and_accepts_lease_args(tmp_path):
    pending, _ = _emit_pending_review(tmp_path)

    list_code = eyes_review_gate.main(["--root", str(tmp_path), "--list-pending"])
    approve_code = eyes_review_gate.main(
        [
            "--root",
            str(tmp_path),
            "--approve",
            pending["review_id"],
            "--decided-by",
            "butcher",
            "--reason",
            "ship it",
            "--principal-id",
            "worker-beta",
            "--capability",
            "android.browser.open_url",
            "--allow-tool",
            "android_browser_open_url",
            "--max-uses",
            "1",
        ]
    )

    assert list_code == 0
    assert approve_code == 0
    assert any((tmp_path / "review" / "approved").glob("*.json"))
