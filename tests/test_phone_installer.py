from __future__ import annotations

import os
import pathlib
import subprocess

INSTALLER = pathlib.Path(__file__).resolve().parents[1] / "install.sh"


def run_installer(*args: str, home: pathlib.Path | None = None):
    env = os.environ.copy()
    if home is not None:
        env["HOME"] = str(home)
    return subprocess.run(
        ["bash", str(INSTALLER), *args],
        capture_output=True,
        env=env,
        text=True,
    )


def test_help_documents_supported_install_modes():
    result = run_installer("--help")

    assert result.returncode == 0
    assert "--dry-run" in result.stdout
    assert "--skip-engine" in result.stdout
    assert "--minimal" in result.stdout
    assert "--upgrade-engine" in result.stdout


def test_dry_run_prints_complete_default_plan(tmp_path):
    result = run_installer("--dry-run", home=tmp_path)

    assert result.returncode == 0, result.stderr
    assert "pkg install -y python rust clang git curl ripgrep libjpeg-turbo" in result.stdout
    assert "pkg install -y android-tools termux-api" in result.stdout
    assert "python -m pipx install code-puppy" in result.stdout
    assert "DroidPuppy/archive/main.tar.gz" in result.stdout
    assert f"{tmp_path}/.code_puppy/plugins" in result.stdout
    assert "code-puppy -i" in result.stdout


def test_minimal_overlay_only_plan_skips_engine_and_optional_tools(tmp_path):
    result = run_installer(
        "--dry-run",
        "--minimal",
        "--skip-engine",
        home=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert "android-tools" not in result.stdout
    assert "termux-api" not in result.stdout
    assert "pipx install code-puppy" not in result.stdout
    assert "DroidPuppy/archive/main.tar.gz" in result.stdout


def test_unknown_option_fails_cleanly():
    result = run_installer("--definitely-not-real")

    assert result.returncode != 0
    assert "Unknown option" in result.stderr


def test_shell_syntax_is_valid():
    result = subprocess.run(
        ["bash", "-n", str(INSTALLER)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
