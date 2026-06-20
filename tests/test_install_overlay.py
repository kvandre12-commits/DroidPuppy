from __future__ import annotations

import importlib.util
import pathlib
import sys
from types import SimpleNamespace

import pytest

MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "scripts" / "install_overlay.py"
)
SPEC = importlib.util.spec_from_file_location("install_overlay", MODULE_PATH)
install_overlay = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = install_overlay
SPEC.loader.exec_module(install_overlay)


def _plugin_names(results):
    return [result.plugin for result in results]


def test_discover_plugins_finds_real_overlay_plugins():
    plugins = install_overlay.discover_plugins()

    assert len(plugins) >= 30
    assert "android_brave_bridge" in {plugin.name for plugin in plugins}
    assert "droidpuppy_doctor" in {plugin.name for plugin in plugins}


def test_resolve_default_user_plugins_dir_falls_back_without_loader(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        install_overlay, "DEFAULT_USER_PLUGINS_DIR", tmp_path / "plugins"
    )
    monkeypatch.setattr(
        install_overlay, "_load_code_puppy_plugins_module", lambda: None
    )

    result = install_overlay.resolve_default_user_plugins_dir()

    assert result == (tmp_path / "plugins")


def test_resolve_default_user_plugins_dir_uses_loader_helper(monkeypatch, tmp_path):
    loader_dir = tmp_path / "loader_plugins"
    loader_module = SimpleNamespace(get_user_plugins_dir=lambda: loader_dir)
    monkeypatch.setattr(
        install_overlay,
        "_load_code_puppy_plugins_module",
        lambda: loader_module,
    )

    result = install_overlay.resolve_default_user_plugins_dir()

    assert result == loader_dir.resolve()


def test_resolve_target_dir_rejects_conflicting_args():
    with pytest.raises(SystemExit, match="either --target-dir or --project-dir"):
        install_overlay.resolve_target_dir(target_dir="/tmp/a", project_dir="/tmp/b")


def test_resolve_target_dir_project_mode(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = install_overlay.resolve_target_dir(project_dir=str(project_dir))

    assert result == project_dir.resolve() / ".code_puppy" / "plugins"


def test_select_plugins_rejects_unknown_names():
    plugins = install_overlay.discover_plugins()

    with pytest.raises(SystemExit, match="Unknown plugin"):
        install_overlay.select_plugins(plugins, ["not-a-real-plugin"])


def test_install_plugins_copy_mode(tmp_path):
    plugins = install_overlay.select_plugins(
        install_overlay.discover_plugins(),
        ["android_brave_bridge", "droidpuppy_doctor"],
    )
    target = tmp_path / "user_plugins"

    results = install_overlay.install_plugins(plugins, target, mode="copy")

    assert _plugin_names(results) == ["android_brave_bridge", "droidpuppy_doctor"]
    assert all(result.status == "installed" for result in results)
    for result in results:
        assert (target / result.plugin / "register_callbacks.py").is_file()
        assert not (target / result.plugin).is_symlink()


def test_install_plugins_symlink_mode(tmp_path):
    plugins = install_overlay.select_plugins(
        install_overlay.discover_plugins(),
        ["android_brave_bridge"],
    )
    target = tmp_path / "user_plugins"

    results = install_overlay.install_plugins(plugins, target, mode="symlink")

    assert results[0].status == "installed"
    assert (target / "android_brave_bridge").is_symlink()


def test_install_plugins_skips_existing_without_overwrite(tmp_path):
    plugins = install_overlay.select_plugins(
        install_overlay.discover_plugins(),
        ["android_brave_bridge"],
    )
    target = tmp_path / "user_plugins"
    target.mkdir(parents=True)
    existing = target / "android_brave_bridge"
    existing.mkdir()
    (existing / "sentinel.txt").write_text("keep me")

    results = install_overlay.install_plugins(plugins, target, mode="copy")

    assert results[0].status == "skipped_exists"
    assert (existing / "sentinel.txt").read_text() == "keep me"


def test_install_plugins_overwrite_replaces_existing_directory(tmp_path):
    plugins = install_overlay.select_plugins(
        install_overlay.discover_plugins(),
        ["android_brave_bridge"],
    )
    target = tmp_path / "user_plugins"
    target.mkdir(parents=True)
    existing = target / "android_brave_bridge"
    existing.mkdir()
    (existing / "sentinel.txt").write_text("old")

    results = install_overlay.install_plugins(
        plugins,
        target,
        mode="copy",
        overwrite=True,
    )

    assert results[0].status == "installed"
    assert not (existing / "sentinel.txt").exists()
    assert (existing / "register_callbacks.py").is_file()


def test_install_plugins_dry_run_does_not_touch_filesystem(tmp_path):
    plugins = install_overlay.select_plugins(
        install_overlay.discover_plugins(),
        ["android_brave_bridge"],
    )
    target = tmp_path / "user_plugins"

    results = install_overlay.install_plugins(
        plugins,
        target,
        mode="copy",
        dry_run=True,
    )

    assert results[0].status == "installed"
    assert not target.exists()


def test_install_plugins_rejects_missing_entrypoint(tmp_path):
    broken = tmp_path / "broken_plugin"
    broken.mkdir()
    target = tmp_path / "user_plugins"

    with pytest.raises(SystemExit, match="missing register_callbacks.py"):
        install_overlay.install_plugins([broken], target, mode="copy")


def test_copied_plugin_is_loader_compatible(tmp_path):
    source_root = tmp_path / "source"
    source_plugin = source_root / "demo_plugin"
    source_plugin.mkdir(parents=True)
    (source_plugin / "register_callbacks.py").write_text(
        "from pathlib import Path\n"
        "(Path(__file__).parent / 'loaded.txt').write_text('ok')\n"
    )
    target = tmp_path / "user_plugins"

    results = install_overlay.install_plugins([source_plugin], target, mode="copy")

    assert results[0].status == "installed"

    sys.path.insert(0, "/data/data/com.termux/files/home/code_puppy_backup_20260617")
    try:
        from code_puppy.plugins import _load_user_plugins

        loaded = _load_user_plugins(target, skip_names=set())
    finally:
        sys.path.remove("/data/data/com.termux/files/home/code_puppy_backup_20260617")
        sys.modules.pop("demo_plugin.register_callbacks", None)
        sys.modules.pop("demo_plugin", None)

    assert loaded == ["demo_plugin"]
    assert (target / "demo_plugin" / "loaded.txt").read_text() == "ok"
