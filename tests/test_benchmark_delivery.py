from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "benchmark_delivery.py"
BASELINE = REPO_ROOT / "baselines" / "june-brave-v1.json"
CONSTRAINTS = REPO_ROOT / "constraints" / "android-0720.txt"
SHOWCASE = REPO_ROOT / "docs" / "BENCHMARK_SHOWCASE.md"
CHART = REPO_ROOT / "docs" / "assets" / "delivery-surface-benchmark.svg"
RECEIPT = REPO_ROOT / "evidence" / "benchmarks" / "delivery-surface-local-20261122.json"
EVIDENCE_README = REPO_ROOT / "evidence" / "benchmarks" / "README.md"

SPEC = importlib.util.spec_from_file_location("benchmark_delivery", SCRIPT)
benchmark_delivery = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(benchmark_delivery)


def test_protected_baseline_measurement_is_bounded():
    metrics = benchmark_delivery.measure_baseline(BASELINE)

    assert metrics["baseline_id"] == "june-brave-v1"
    assert metrics["engine_policy"] == "reuse-only"
    assert metrics["package_install_count"] == 0
    assert metrics["plugin_count"] == 7
    assert metrics["plugin_file_count"] == 21
    assert metrics["plugin_bytes"] > 0
    assert metrics["missing_plugins"] == []
    assert metrics["plugin_integrity_valid"] is True
    assert metrics["plugin_integrity_errors"] == []
    assert len(metrics["plugin_tree_sha256_actual"]) == 7


def test_equal_size_plugin_mutation_fails_benchmark_integrity(tmp_path):
    case_root = tmp_path / "case"
    baseline_dir = case_root / "baselines"
    plugin_root = case_root / "code_puppy" / "plugins"
    baseline_dir.mkdir(parents=True)
    manifest = json.loads(BASELINE.read_text())
    copied_baseline = baseline_dir / BASELINE.name
    shutil.copy2(BASELINE, copied_baseline)
    for plugin in manifest["plugins"]:
        shutil.copytree(
            REPO_ROOT / "code_puppy" / "plugins" / plugin,
            plugin_root / plugin,
        )

    victim = plugin_root / "android_brave_bridge" / "tooling.py"
    original = victim.read_bytes()
    mutated = bytearray(original)
    mutated[0] ^= 1
    victim.write_bytes(mutated)
    assert victim.stat().st_size == len(original)

    metrics = benchmark_delivery.measure_baseline(copied_baseline)

    assert metrics["plugin_bytes"] == 76318
    assert metrics["plugin_integrity_valid"] is False
    assert metrics["plugin_integrity_errors"] == [
        "plugin tree checksum mismatch: android_brave_bridge"
    ]
    with pytest.raises(ValueError, match="protected baseline integrity failed"):
        benchmark_delivery.measure_target("mutated", copied_baseline)


def test_constraints_measurement_counts_exact_closure():
    metrics = benchmark_delivery.measure_constraints(CONSTRAINTS)

    assert metrics["constraint_count"] == 88
    assert metrics["exact_pin_count"] == 88
    assert metrics["sensitive_families"] == []


def test_pyproject_measurement_counts_git_sources_and_lock(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "example-agent"
version = "1.2.3"
dependencies = [
  "pydantic-ai-pax[boxd,modal]",
  "playwright==1.0",
]
[tool.uv.sources]
pydantic-ai-pax = { git = "https://example.invalid/repo", rev = "abc" }
""".strip()
    )
    (tmp_path / "uv.lock").write_text(
        """
version = 1
[[package]]
name = "example-agent"
version = "1.2.3"
source = { editable = "." }
[[package]]
name = "pydantic-ai-pax"
version = "1.0.0"
source = { git = "https://example.invalid/repo?rev=abc" }
[[package]]
name = "tree-sitter-rust"
version = "1.0.0"
source = { registry = "https://example.invalid" }
""".strip()
    )

    metrics = benchmark_delivery.measure_pyproject(pyproject)

    assert metrics["declared_dependency_count"] == 2
    assert metrics["exact_pinned_dependency_count"] == 1
    assert metrics["requested_extras"] == ["boxd", "modal"]
    assert metrics["direct_git_source_count"] == 1
    assert metrics["locked_package_count"] == 3
    assert metrics["locked_git_source_count"] == 1
    assert metrics["declared_sensitive_families"] == [
        "pydantic-ai-pax",
        "playwright",
    ]
    assert metrics["locked_sensitive_families"] == [
        "pydantic-ai-pax",
        "tree-sitter",
    ]


def test_receipt_disclaims_unmeasured_claims():
    receipt = benchmark_delivery.build_receipt(
        [f"june={BASELINE}", f"android-0720={CONSTRAINTS}"]
    )

    assert receipt["claims"] == {
        "measures_architecture_not_model_quality": True,
        "performs_installs": False,
        "uses_network": False,
        "proves_token_efficiency": False,
        "proves_security": False,
    }
    assert [target["label"] for target in receipt["targets"]] == [
        "june",
        "android-0720",
    ]


def test_cli_writes_same_machine_readable_receipt(tmp_path):
    output = tmp_path / "receipt.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target",
            f"june={BASELINE}",
            "--target",
            f"android-0720={CONSTRAINTS}",
            "--output",
            str(output),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == json.loads(output.read_text())


def test_showcase_matches_published_receipt():
    receipt = json.loads(RECEIPT.read_text())
    metrics = {target["label"]: target["metrics"] for target in receipt["targets"]}
    showcase = SHOWCASE.read_text()

    june = metrics["june-brave-v1"]
    assert f"{june['plugin_count']} plugins" in showcase
    assert f"{june['plugin_file_count']} files" in showcase
    assert f"{june['plugin_bytes']:,} bytes" in showcase
    assert str(metrics["android-0720"]["constraint_count"]) in showcase
    for label in ("puppy-0759", "puppy-0890", "puppy-v1"):
        assert str(metrics[label]["locked_package_count"]) in showcase


def test_published_receipt_hash_is_synchronized():
    digest = hashlib.sha256(RECEIPT.read_bytes()).hexdigest()

    assert digest in SHOWCASE.read_text()
    assert digest in CHART.read_text()
    assert digest in EVIDENCE_README.read_text()


def test_showcase_chart_is_valid_svg():
    root = ET.parse(CHART).getroot()

    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.attrib["role"] == "img"


def test_cli_rejects_malformed_target():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--target", "missing-separator"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode != 0
    assert "LABEL=PATH" in completed.stderr
