from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys

from scripts import baseline_integrity

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "baselines" / "june-brave-v1.json"
VERIFIER = REPO_ROOT / "scripts" / "verify_baseline.py"

SPEC = importlib.util.spec_from_file_location("verify_baseline", VERIFIER)
verify_baseline = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(verify_baseline)


def test_june_baseline_contract_is_valid():
    receipt = verify_baseline.verify_baseline("june-brave-v1")

    assert receipt["valid"] is True
    assert receipt["engine_policy"] == "reuse-only"
    assert receipt["package_install_count"] == 0
    assert receipt["plugins"] == list(verify_baseline.EXPECTED_PLUGINS)


def test_june_baseline_preserves_original_provenance():
    manifest = json.loads(MANIFEST.read_text())

    assert manifest["origin"] == {
        "repository": "kvandre12-commits/DroidPuppy",
        "commit": "275bd5a8c9f4023a56be08cc454af585e3586d3f",
        "date": "2026-06-13",
        "title": "Initial DroidPuppy Android toolkit",
    }


def test_june_baseline_freezes_plugin_implementation_bytes():
    manifest = json.loads(MANIFEST.read_text())

    expected_hashes = manifest["plugin_tree_sha256"]
    assert set(expected_hashes) == set(verify_baseline.EXPECTED_PLUGINS)
    for plugin in verify_baseline.EXPECTED_PLUGINS:
        plugin_dir = verify_baseline.PLUGINS_DIR / plugin
        assert (
            baseline_integrity.plugin_tree_sha256(plugin_dir) == expected_hashes[plugin]
        )


def test_verifier_rejects_plugin_implementation_drift(monkeypatch, tmp_path):
    plugins_dir = tmp_path / "plugins"
    for plugin in verify_baseline.EXPECTED_PLUGINS:
        shutil.copytree(verify_baseline.PLUGINS_DIR / plugin, plugins_dir / plugin)
    (plugins_dir / "android_brave_bridge" / "tooling.py").write_text("# surprise\n")
    monkeypatch.setattr(verify_baseline, "PLUGINS_DIR", plugins_dir)

    receipt = verify_baseline.verify_baseline("june-brave-v1")

    assert receipt["valid"] is False
    assert "plugin tree checksum mismatch: android_brave_bridge" in receipt["errors"]


def test_june_baseline_blocks_dependency_expansion():
    manifest = json.loads(MANIFEST.read_text())

    assert manifest["package_installs"] == []
    assert {
        "pydantic-ai-pax",
        "pydantic-ai-harness",
        "pydantic-monty",
        "playwright",
        "tree-sitter",
    } <= set(manifest["forbidden_dependencies"])
    assert "sync-all-groups" in manifest["forbidden_operations"]
    assert "build-upstream-pydantic-ai" in manifest["forbidden_operations"]


def test_verifier_cli_emits_machine_readable_receipt():
    completed = subprocess.run(
        [sys.executable, str(VERIFIER), "june-brave-v1"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    receipt = json.loads(completed.stdout)
    assert receipt["valid"] is True
    assert receipt["baseline_id"] == "june-brave-v1"


def test_unknown_baseline_fails_closed():
    completed = subprocess.run(
        [sys.executable, str(VERIFIER), "latest-circus"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 1
    assert json.loads(completed.stdout)["valid"] is False
