#!/usr/bin/env python3
"""Install DroidPuppy plugins into Code Puppy's user/project plugin tiers.

Default target is the user plugin directory ``~/.code_puppy/plugins`` so
people can install upstream Code Puppy however they want and then layer
DroidPuppy on top without mutating site-packages or Mike's checkout.
"""

from __future__ import annotations

import argparse
import importlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_PLUGINS_DIR = REPO_ROOT / "code_puppy" / "plugins"
DEFAULT_USER_PLUGINS_DIR = Path.home() / ".code_puppy" / "plugins"


@dataclass(frozen=True)
class InstallResult:
    plugin: str
    status: str
    destination: Path


def _load_code_puppy_plugins_module() -> ModuleType | None:
    """Best-effort import of Code Puppy's plugin loader module."""
    try:
        module = importlib.import_module("code_puppy.plugins")
    except Exception:
        return None
    return module


def resolve_default_user_plugins_dir() -> Path:
    """Resolve the user plugin dir from Code Puppy itself when possible."""
    module = _load_code_puppy_plugins_module()
    getter = getattr(module, "get_user_plugins_dir", None) if module else None
    if callable(getter):
        try:
            resolved = getter()
            if resolved is not None:
                return Path(resolved).expanduser().resolve()
        except Exception:
            pass
    return DEFAULT_USER_PLUGINS_DIR


def discover_plugins(source_dir: Path = SOURCE_PLUGINS_DIR) -> list[Path]:
    """Return installable plugin directories sorted by name."""
    if not source_dir.is_dir():
        raise SystemExit(f"Source plugins directory not found: {source_dir}")

    plugins: list[Path] = []
    for entry in sorted(source_dir.iterdir(), key=lambda path: path.name.lower()):
        if not entry.is_dir() or entry.name.startswith((".", "_")):
            continue
        if (entry / "register_callbacks.py").is_file():
            plugins.append(entry)
    return plugins


def resolve_target_dir(
    *,
    target_dir: str | None = None,
    project_dir: str | None = None,
) -> Path:
    """Resolve the final plugin directory for user or project installs."""
    if target_dir and project_dir:
        raise SystemExit("Choose either --target-dir or --project-dir, not both")
    if target_dir:
        return Path(target_dir).expanduser().resolve()
    if project_dir:
        return Path(project_dir).expanduser().resolve() / ".code_puppy" / "plugins"
    return resolve_default_user_plugins_dir()


def select_plugins(available: list[Path], names: list[str] | None) -> list[Path]:
    """Filter the discovered plugin list to the requested names."""
    if not names:
        return available

    by_name = {plugin.name: plugin for plugin in available}
    missing = [name for name in names if name not in by_name]
    if missing:
        missing_str = ", ".join(sorted(missing))
        raise SystemExit(f"Unknown plugin(s): {missing_str}")
    return [by_name[name] for name in names]


def _remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _validate_plugin_dir(plugin_dir: Path) -> None:
    callbacks = plugin_dir / "register_callbacks.py"
    if not callbacks.is_file():
        raise SystemExit(
            f"Plugin '{plugin_dir.name}' is missing register_callbacks.py: {callbacks}"
        )


def install_plugins(
    plugins: list[Path],
    target_dir: Path,
    *,
    mode: str = "copy",
    overwrite: bool = False,
    dry_run: bool = False,
) -> list[InstallResult]:
    """Install the selected plugin directories into ``target_dir``."""
    results: list[InstallResult] = []
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    for plugin_dir in plugins:
        _validate_plugin_dir(plugin_dir)
        destination = target_dir / plugin_dir.name
        if destination.exists() or destination.is_symlink():
            if not overwrite:
                results.append(
                    InstallResult(
                        plugin=plugin_dir.name,
                        status="skipped_exists",
                        destination=destination,
                    )
                )
                continue
            if not dry_run:
                _remove_existing(destination)

        if not dry_run:
            if mode == "copy":
                shutil.copytree(plugin_dir, destination)
            elif mode == "symlink":
                destination.symlink_to(plugin_dir.resolve(), target_is_directory=True)
            else:  # pragma: no cover - argparse constrains this
                raise ValueError(f"Unsupported mode: {mode}")

        results.append(
            InstallResult(
                plugin=plugin_dir.name, status="installed", destination=destination
            )
        )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install DroidPuppy as a Code Puppy plugin overlay."
    )
    parser.add_argument(
        "--project-dir",
        help="Install into <project>/.code_puppy/plugins instead of ~/.code_puppy/plugins.",
    )
    parser.add_argument(
        "--target-dir",
        help="Install into an explicit plugins directory (mostly for custom setups/tests).",
    )
    parser.add_argument(
        "--mode",
        choices=("copy", "symlink"),
        default="copy",
        help="Install by copying directories or symlinking them.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing plugin directories at the destination.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without touching the filesystem.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available DroidPuppy plugins and exit.",
    )
    parser.add_argument(
        "--plugins",
        nargs="+",
        metavar="PLUGIN",
        help="Install only the named plugins instead of the full overlay.",
    )
    return parser


def _print_summary(
    results: list[InstallResult], target_dir: Path, dry_run: bool
) -> None:
    installed = [result for result in results if result.status == "installed"]
    skipped = [result for result in results if result.status == "skipped_exists"]
    action = "Would install" if dry_run else "Installed"
    print(f"{action} {len(installed)} plugin(s) into {target_dir}")
    for result in installed:
        print(f"  + {result.plugin}")
    if skipped:
        print(f"Skipped {len(skipped)} existing plugin(s):")
        for result in skipped:
            print(f"  = {result.plugin}")
    if not dry_run and installed:
        print("\nNext steps:")
        print("  1. Start Code Puppy from Mike's upstream install/checkout.")
        print("  2. Run the DroidPuppy doctor tool to verify Android readiness.")
        print(
            "  3. If you want CDP browser control, install adb: pkg install android-tools"
        )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    available = discover_plugins()
    if not available:
        raise SystemExit(f"No installable plugins found under {SOURCE_PLUGINS_DIR}")

    if args.list:
        for plugin in available:
            print(plugin.name)
        return 0

    selected = select_plugins(available, args.plugins)
    target_dir = resolve_target_dir(
        target_dir=args.target_dir,
        project_dir=args.project_dir,
    )
    results = install_plugins(
        selected,
        target_dir,
        mode=args.mode,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    _print_summary(results, target_dir, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
