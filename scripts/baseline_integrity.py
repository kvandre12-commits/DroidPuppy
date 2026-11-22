"""Shared deterministic integrity checks for protected plugin baselines."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def plugin_tree_sha256(plugin_dir: Path) -> str:
    """Hash relative file names and bytes in a plugin tree deterministically."""
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


def verify_plugin_trees(
    plugin_root: Path,
    plugins: Any,
    expected_hashes: Any,
) -> dict[str, object]:
    """Return actual hashes and errors for a protected plugin allowlist."""
    errors: list[str] = []
    actual_hashes: dict[str, str] = {}

    if not isinstance(plugins, list) or not all(
        isinstance(plugin, str) for plugin in plugins
    ):
        return {
            "valid": False,
            "errors": ["plugins must be a list of names"],
            "actual_hashes": actual_hashes,
        }
    if not isinstance(expected_hashes, dict):
        return {
            "valid": False,
            "errors": ["plugin_tree_sha256 must be an object"],
            "actual_hashes": actual_hashes,
        }

    unexpected_hashes = sorted(set(expected_hashes) - set(plugins))
    if unexpected_hashes:
        errors.append(
            "hashes declared for plugins outside allowlist: "
            + ", ".join(unexpected_hashes)
        )

    for plugin in plugins:
        expected = expected_hashes.get(plugin)
        if not isinstance(expected, str) or len(expected) != 64:
            errors.append(f"missing or malformed plugin tree checksum: {plugin}")
            continue
        plugin_dir = plugin_root / plugin
        callbacks = plugin_dir / "register_callbacks.py"
        if not callbacks.is_file():
            errors.append(f"missing plugin entrypoint: {plugin}")
            continue
        actual = plugin_tree_sha256(plugin_dir)
        actual_hashes[plugin] = actual
        if actual != expected:
            errors.append(f"plugin tree checksum mismatch: {plugin}")

    return {
        "valid": not errors,
        "errors": errors,
        "actual_hashes": actual_hashes,
    }
