#!/usr/bin/env python3
"""Verify protected DroidPuppy baseline contracts without importing Code Puppy."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINES_DIR = REPO_ROOT / "baselines"
PLUGINS_DIR = REPO_ROOT / "code_puppy" / "plugins"
EXPECTED_PLUGINS = (
    "android_brave_bridge",
    "android_browser_actions",
    "android_browser_easy",
    "android_cdp_bridge",
    "android_cdp_client",
    "android_friendly_router",
    "android_utility_kit",
)
REQUIRED_FORBIDDEN_DEPENDENCIES = {
    "pydantic-ai-pax",
    "pydantic-ai-harness",
    "pydantic-monty",
    "playwright",
    "tree-sitter",
}
REQUIRED_FORBIDDEN_OPERATIONS = {
    "install-engine",
    "repair-engine",
    "sync-all-groups",
    "upgrade-engine",
    "build-upstream-pydantic-ai",
}


def plugin_tree_sha256(plugin_dir: Path) -> str:
    """Hash file names and bytes in a plugin tree deterministically."""
    digest = hashlib.sha256()
    for path in sorted(plugin_dir.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(plugin_dir).as_posix().encode()
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def load_baseline(baseline_id: str) -> dict[str, object]:
    path = BASELINES_DIR / f"{baseline_id}.json"
    if not path.is_file():
        raise ValueError(f"unknown baseline: {baseline_id}")
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise TypeError("baseline document must be a JSON object")
    return data


def verify_baseline(baseline_id: str) -> dict[str, object]:
    data = load_baseline(baseline_id)
    errors: list[str] = []

    if data.get("schema_version") != 1:
        errors.append("schema_version must equal 1")
    if data.get("baseline_id") != baseline_id:
        errors.append("baseline_id does not match its filename")
    if data.get("status") != "protected":
        errors.append("status must remain protected")
    if data.get("engine_policy") != "reuse-only":
        errors.append("engine_policy must remain reuse-only")
    if data.get("package_installs") != []:
        errors.append("package_installs must remain empty")

    plugins = data.get("plugins")
    expected_hashes = data.get("plugin_tree_sha256")
    if plugins != list(EXPECTED_PLUGINS):
        errors.append("plugin allowlist differs from the June 2026 baseline")
    elif not isinstance(expected_hashes, dict):
        errors.append("plugin_tree_sha256 must be an object")
    else:
        for plugin in EXPECTED_PLUGINS:
            plugin_dir = PLUGINS_DIR / plugin
            callbacks = plugin_dir / "register_callbacks.py"
            if not callbacks.is_file():
                errors.append(f"missing plugin entrypoint: {plugin}")
                continue
            actual_hash = plugin_tree_sha256(plugin_dir)
            if expected_hashes.get(plugin) != actual_hash:
                errors.append(f"plugin tree checksum mismatch: {plugin}")

    forbidden_dependencies = set(data.get("forbidden_dependencies", []))
    missing_dependencies = REQUIRED_FORBIDDEN_DEPENDENCIES - forbidden_dependencies
    if missing_dependencies:
        errors.append(
            "missing forbidden dependencies: " + ", ".join(sorted(missing_dependencies))
        )

    forbidden_operations = set(data.get("forbidden_operations", []))
    missing_operations = REQUIRED_FORBIDDEN_OPERATIONS - forbidden_operations
    if missing_operations:
        errors.append(
            "missing forbidden operations: " + ", ".join(sorted(missing_operations))
        )

    return {
        "baseline_id": baseline_id,
        "valid": not errors,
        "errors": errors,
        "engine_policy": data.get("engine_policy"),
        "package_install_count": len(data.get("package_installs", [])),
        "plugins": data.get("plugins", []),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", nargs="?", default="june-brave-v1")
    args = parser.parse_args(argv)

    try:
        receipt = verify_baseline(args.baseline)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        receipt = {
            "baseline_id": args.baseline,
            "valid": False,
            "errors": [str(exc)],
        }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
