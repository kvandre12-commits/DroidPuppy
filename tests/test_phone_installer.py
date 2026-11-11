from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
import subprocess
import tarfile

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "install.sh"
CONSTRAINTS = REPO_ROOT / "constraints" / "android-0720.txt"
BASH = shutil.which("bash") or "bash"


def run_installer(
    *args: str,
    home: pathlib.Path | None = None,
    path: pathlib.Path | None = None,
    extra_env: dict[str, str] | None = None,
):
    env = os.environ.copy()
    if home is not None:
        env["HOME"] = str(home)
    if path is not None:
        env["PATH"] = str(path)
    if extra_env is not None:
        env.update(extra_env)
    return subprocess.run(
        [BASH, str(INSTALLER), *args],
        capture_output=True,
        env=env,
        text=True,
    )


def isolated_path(tmp_path: pathlib.Path, *, include_engine: bool = False) -> pathlib.Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cat = shutil.which("cat")
    assert cat is not None
    (bin_dir / "cat").symlink_to(cat)
    if include_engine:
        executable = bin_dir / "code-puppy"
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
    return bin_dir


def test_help_documents_supported_install_modes():
    result = run_installer("--help")

    assert result.returncode == 0
    assert "--dry-run" in result.stdout
    assert "--skip-engine" in result.stdout
    assert "--minimal" in result.stdout
    assert "--engine-profile" in result.stdout
    assert "--upgrade-engine" not in result.stdout


def test_dry_run_prints_complete_default_plan(tmp_path):
    result = run_installer(
        "--dry-run", home=tmp_path, path=isolated_path(tmp_path)
    )

    assert result.returncode == 0, result.stderr
    assert "pkg install -y python rust clang git curl ripgrep libjpeg-turbo" in result.stdout
    assert "pkg install -y android-tools termux-api" in result.stdout
    assert "code-puppy==0.0.720" in result.stdout
    assert "--backend pip" in result.stdout
    assert "--constraint" in result.stdout
    assert "pipx install code-puppy" not in result.stdout
    assert "DroidPuppy/archive/main.tar.gz" in result.stdout
    assert "android-0720.txt" in result.stdout
    assert f"{tmp_path}/.code_puppy/plugins" in result.stdout
    assert "code-puppy -i" in result.stdout


def test_minimal_overlay_only_plan_skips_engine_and_optional_tools(tmp_path):
    result = run_installer(
        "--dry-run",
        "--minimal",
        "--skip-engine",
        home=tmp_path,
        path=isolated_path(tmp_path),
    )

    assert result.returncode == 0, result.stderr
    assert "android-tools" not in result.stdout
    assert "termux-api" not in result.stdout
    assert "pipx install code-puppy" not in result.stdout
    assert "DroidPuppy/archive/main.tar.gz" in result.stdout


def test_existing_engine_is_never_mutated_by_default(tmp_path):
    bin_dir = isolated_path(tmp_path, include_engine=True)

    result = run_installer("--dry-run", home=tmp_path, path=bin_dir)

    assert result.returncode == 0, result.stderr
    assert "already installed; leaving its version unchanged" in result.stdout
    assert "pipx install" not in result.stdout
    assert "pipx upgrade" not in result.stdout


def _write_executable(path: pathlib.Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def test_hermetic_fresh_install_uses_pinned_profile(tmp_path):
    source = tmp_path / "source" / "DroidPuppy-test"
    (source / "constraints").mkdir(parents=True)
    (source / "scripts").mkdir()
    shutil.copy2(CONSTRAINTS, source / "constraints" / CONSTRAINTS.name)
    (source / "scripts" / "install_overlay.py").write_text("# fixture\n")
    archive = tmp_path / "droidpuppy.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(source, arcname=source.name)

    bin_dir = tmp_path / "mock-bin"
    bin_dir.mkdir()
    for command in (
        "cat",
        "find",
        "gzip",
        "head",
        "mktemp",
        "rm",
        "sha256sum",
        "tar",
        "tr",
        "wc",
    ):
        executable = shutil.which(command)
        assert executable is not None
        (bin_dir / command).symlink_to(executable)

    python = shutil.which("python")
    assert python is not None
    _write_executable(
        bin_dir / "pkg",
        f"#!{python}\n"
        "import os, pathlib, sys\n"
        "pathlib.Path(os.environ['HOME'], 'commands.log').open('a').write("
        "'pkg ' + ' '.join(sys.argv[1:]) + '\\n')\n",
    )
    _write_executable(
        bin_dir / "curl",
        f"#!{python}\n"
        "import os, pathlib, shutil, sys\n"
        "args = sys.argv[1:]\n"
        "target = pathlib.Path(args[args.index('-o') + 1])\n"
        "shutil.copy2(os.environ['FIXTURE_ARCHIVE'], target)\n",
    )
    _write_executable(
        bin_dir / "python",
        f"#!{python}\n"
        "import os, pathlib, sys\n"
        "home = pathlib.Path(os.environ['HOME'])\n"
        "args = sys.argv[1:]\n"
        "home.joinpath('commands.log').open('a').write("
        "'python ' + ' '.join(args) + '\\n')\n"
        "if 'pipx' in args and 'install' in args:\n"
        "    app = home / '.local/bin/code-puppy'\n"
        "    app.parent.mkdir(parents=True, exist_ok=True)\n"
        "    app.write_text('#!/bin/sh\\nexit 0\\n')\n"
        "    app.chmod(0o755)\n"
        "if args and args[-1] == '--overwrite':\n"
        "    plugin = home / '.code_puppy/plugins/fixture'\n"
        "    plugin.mkdir(parents=True, exist_ok=True)\n"
        "    plugin.joinpath('register_callbacks.py').write_text('# fixture\\n')\n",
    )

    result = run_installer(
        "--minimal",
        home=tmp_path,
        path=bin_dir,
        extra_env={
            "FIXTURE_ARCHIVE": str(archive),
            "PREFIX": "/data/data/com.termux/files/usr",
        },
    )

    assert result.returncode == 0, result.stderr
    commands = (tmp_path / "commands.log").read_text()
    assert "pipx install --backend pip" in commands
    assert "--constraint" in commands
    assert "code-puppy==0.0.720" in commands
    assert "pipx upgrade" not in commands
    assert "plugins:    1" in result.stdout


def test_unknown_engine_profile_fails_closed():
    result = run_installer("--dry-run", "--engine-profile", "latest-maybe-lol")

    assert result.returncode != 0
    assert "Unknown engine profile" in result.stderr


def test_android_profile_excludes_unvalidated_native_dependencies():
    requirements = {
        line.strip().lower()
        for line in CONSTRAINTS.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }

    assert len(requirements) == 88
    assert not any("monty" in requirement for requirement in requirements)
    assert not any("tree-sitter" in requirement for requirement in requirements)


def test_installer_embeds_constraints_checksum():
    digest = hashlib.sha256(CONSTRAINTS.read_bytes()).hexdigest()

    assert digest in INSTALLER.read_text()


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
