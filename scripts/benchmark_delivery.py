#!/usr/bin/env python3
"""Produce offline, machine-readable agent delivery-surface measurements."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import tomllib

SCHEMA_VERSION = 1
NAME_PATTERN = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
EXTRAS_PATTERN = re.compile(r"^[A-Za-z0-9._-]+\[([^]]+)]")
SENSITIVE_FAMILIES = (
    "pydantic-ai-pax",
    "pydantic-ai-harness",
    "pydantic-monty",
    "playwright",
    "tree-sitter",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def dependency_name(requirement: str) -> str:
    match = NAME_PATTERN.match(requirement)
    if not match:
        raise ValueError(f"cannot parse dependency name: {requirement!r}")
    return normalize_name(match.group(1))


def requested_extras(requirement: str) -> set[str]:
    match = EXTRAS_PATTERN.match(requirement.strip())
    if not match:
        return set()
    return {extra.strip() for extra in match.group(1).split(",") if extra.strip()}


def sensitive_families(names: set[str]) -> list[str]:
    found: list[str] = []
    for family in SENSITIVE_FAMILIES:
        if family == "tree-sitter":
            present = any(
                name == family or name.startswith(f"{family}-") for name in names
            )
        else:
            present = family in names
        if present:
            found.append(family)
    return found


def measure_lock(lock_path: Path) -> dict[str, object]:
    if not lock_path.is_file():
        return {
            "lock_present": False,
            "locked_package_count": None,
            "locked_git_source_count": None,
        }
    data = tomllib.loads(lock_path.read_text())
    packages = data.get("package", [])
    names = {
        normalize_name(package["name"])
        for package in packages
        if isinstance(package, dict) and isinstance(package.get("name"), str)
    }
    git_sources = sum(
        1
        for package in packages
        if isinstance(package, dict)
        and isinstance(package.get("source"), dict)
        and "git" in package["source"]
    )
    return {
        "lock_present": True,
        "lock_sha256": sha256_file(lock_path),
        "locked_package_count": len(packages),
        "locked_git_source_count": git_sources,
        "locked_sensitive_families": sensitive_families(names),
    }


def measure_pyproject(path: Path) -> dict[str, object]:
    data = tomllib.loads(path.read_text())
    project = data.get("project", {})
    dependencies = project.get("dependencies", [])
    if not isinstance(dependencies, list) or not all(
        isinstance(item, str) for item in dependencies
    ):
        raise ValueError(f"invalid project.dependencies in {path}")
    names = {dependency_name(item) for item in dependencies}
    extras = set().union(*(requested_extras(item) for item in dependencies))
    sources = data.get("tool", {}).get("uv", {}).get("sources", {})
    direct_git_sources = sum(
        1
        for source in sources.values()
        if isinstance(source, dict) and isinstance(source.get("git"), str)
    )
    result: dict[str, object] = {
        "kind": "pyproject",
        "project_name": project.get("name"),
        "project_version": project.get("version"),
        "declared_dependency_count": len(dependencies),
        "exact_pinned_dependency_count": sum("==" in item for item in dependencies),
        "requested_extra_count": len(extras),
        "requested_extras": sorted(extras),
        "direct_git_source_count": direct_git_sources,
        "declared_sensitive_families": sensitive_families(names),
    }
    result.update(measure_lock(path.with_name("uv.lock")))
    return result


def _requirement_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def measure_constraints(path: Path) -> dict[str, object]:
    requirements = _requirement_lines(path)
    names = {dependency_name(item) for item in requirements}
    return {
        "kind": "constraints",
        "constraint_count": len(requirements),
        "exact_pin_count": sum("==" in item for item in requirements),
        "sensitive_families": sensitive_families(names),
    }


def measure_baseline(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise TypeError("baseline must be a JSON object")
    plugins = data.get("plugins", [])
    package_installs = data.get("package_installs", [])
    plugin_root = path.parent.parent / "code_puppy" / "plugins"
    plugin_files: list[Path] = []
    missing_plugins: list[str] = []
    for plugin in plugins:
        plugin_dir = plugin_root / plugin
        if not plugin_dir.is_dir():
            missing_plugins.append(plugin)
            continue
        plugin_files.extend(
            file
            for file in plugin_dir.rglob("*")
            if file.is_file() and "__pycache__" not in file.parts
        )
    return {
        "kind": "protected-baseline",
        "baseline_id": data.get("baseline_id"),
        "engine_policy": data.get("engine_policy"),
        "package_install_count": len(package_installs),
        "plugin_count": len(plugins),
        "plugin_file_count": len(plugin_files),
        "plugin_bytes": sum(file.stat().st_size for file in plugin_files),
        "missing_plugins": sorted(missing_plugins),
        "forbidden_dependencies": data.get("forbidden_dependencies", []),
        "forbidden_operations": data.get("forbidden_operations", []),
    }


def measure_target(label: str, path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"target does not exist: {path}")
    if path.name == "pyproject.toml":
        metrics = measure_pyproject(path)
    elif path.suffix == ".json":
        metrics = measure_baseline(path)
    elif path.suffix == ".txt":
        metrics = measure_constraints(path)
    else:
        raise ValueError(f"unsupported target type: {path}")
    return {
        "label": label,
        "input_name": path.name,
        "input_sha256": sha256_file(path),
        "metrics": metrics,
    }


def parse_target(value: str) -> tuple[str, Path]:
    label, separator, raw_path = value.partition("=")
    if not separator or not label or not raw_path:
        raise ValueError("target must use LABEL=PATH")
    return label, Path(raw_path).expanduser().resolve()


def build_receipt(targets: list[str]) -> dict[str, object]:
    measured = []
    for target in targets:
        label, path = parse_target(target)
        measured.append(measure_target(label, path))
    return {
        "schema_version": SCHEMA_VERSION,
        "benchmark": "delivery-surface",
        "claims": {
            "measures_architecture_not_model_quality": True,
            "performs_installs": False,
            "uses_network": False,
            "proves_token_efficiency": False,
            "proves_security": False,
        },
        "targets": measured,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        action="append",
        required=True,
        metavar="LABEL=PATH",
        help="Measure a baseline JSON, constraints TXT, or pyproject.toml.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON receipt path.")
    args = parser.parse_args(argv)

    try:
        receipt = build_receipt(args.target)
    except (
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        tomllib.TOMLDecodeError,
    ) as exc:
        parser.error(str(exc))
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
