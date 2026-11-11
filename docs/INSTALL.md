# Installation

## Goal

DroidPuppy is meant to layer on top of **Mike's upstream Code Puppy install**
without editing site-packages or mutating the upstream checkout.

This is the **light installer** path: keep the engine upstream, keep the
Android-native product layer here, and connect them through Code Puppy's plugin
contract instead of repo-sprawl goblinry.

The preferred install target is Code Puppy's **user plugin tier**:

```text
~/.code_puppy/plugins/
```

That works whether Code Puppy came from `uvx`, `pip`, or a git checkout.

The installer follows Code Puppy's real plugin-tier contract: it targets the
loader's user plugin path when available and only installs plugin directories
that expose a loadable `register_callbacks.py` entrypoint.

## One-command phone install

Install a current Termux build from F-Droid or the official Termux GitHub
releases. Do not use the obsolete Google Play build. Open Termux and paste:

```bash
pkg install -y curl && curl -fsSL https://raw.githubusercontent.com/kvandre12-commits/DroidPuppy/main/install.sh | bash
```

This installs the complete stack:

1. Termux's Python, Rust, Clang, Git, curl, ripgrep, and Pillow build support.
2. Optional Android helpers (`adb` and Termux:API commands).
3. The pinned pipx bootstrap used by the `android-0720` profile.
4. The pinned `android-0720` engine profile in an isolated pipx environment.
5. Code Puppy `0.0.720` through pipx's pip backend and the profile's exact
   constraints file.
6. DroidPuppy plugins under `~/.code_puppy/plugins`.
7. A final executable and plugin-count verification.

The installer verifies the constraints file by SHA-256 before using it. The
profile excludes Monty/code mode and the mandatory Tree-sitter grammar bundle
introduced by newer, unvalidated engine releases. It is currently a recovery
candidate and must pass a clean-phone install before being advertised as a
validated release.

The first install may take 10–20 minutes because Android may compile native
Python packages. Keep Termux open and the phone awake. The installer is
idempotent: rerunning it refreshes the DroidPuppy overlay and **never mutates an
already-installed engine**.

Start the agent after installation:

```bash
code-puppy -i
```

### Installer options

Pass options after `bash -s --` when running through curl:

```bash
# Show every action without changing the phone
curl -fsSL https://raw.githubusercontent.com/kvandre12-commits/DroidPuppy/main/install.sh | bash -s -- --dry-run

# Refresh DroidPuppy when Code Puppy is already installed
curl -fsSL https://raw.githubusercontent.com/kvandre12-commits/DroidPuppy/main/install.sh | bash -s -- --skip-engine

# Avoid optional ADB and Termux:API packages
curl -fsSL https://raw.githubusercontent.com/kvandre12-commits/DroidPuppy/main/install.sh | bash -s -- --minimal

# Replace a broken/partial pipx engine with the exact recovery profile
curl -fsSL https://raw.githubusercontent.com/kvandre12-commits/DroidPuppy/main/install.sh | bash -s -- --repair-engine

# Select the known Android recovery profile explicitly (it is also the default)
curl -fsSL https://raw.githubusercontent.com/kvandre12-commits/DroidPuppy/main/install.sh | bash -s -- --engine-profile android-0720
```

### Manual developer install

Contributors can still install only the overlay from a source checkout:

```bash
python scripts/install_overlay.py --overwrite
```

That copies every DroidPuppy plugin in this repo into:

```text
~/.code_puppy/plugins/
```

### Project-local install

If you want the overlay only for one checkout:

```bash
python scripts/install_overlay.py --project-dir /path/to/project
```

That installs into:

```text
/path/to/project/.code_puppy/plugins/
```

### Development / live-edit install

If you're actively working on DroidPuppy itself, symlink the plugins instead of
copying them:

```bash
python scripts/install_overlay.py --mode symlink --overwrite
```

### Plugin inventory

List the available plugins without installing them:

```bash
python scripts/install_overlay.py --list
```

The full plugin/tool catalog lives in [`PLUGIN_REFERENCE.md`](PLUGIN_REFERENCE.md).
For the engine/overlay framing, read
[`UPSTREAM_ENGINE_AND_OVERLAY.md`](UPSTREAM_ENGINE_AND_OVERLAY.md).

### Verify the stack after install

Start Code Puppy, then run the DroidPuppy doctor tool to check platform,
Android commands, browser availability, optional ADB/CDP readiness, and plugin
inventory.

## Troubleshooting

If `code-puppy` is not found immediately after a successful install, close and
reopen Termux so its updated PATH is loaded, then run `code-puppy -i` again.
Use the full installer again to refresh the DroidPuppy overlay. It deliberately
has no generic upgrade switch: changing engine versions requires a separately
reviewed and checksummed profile rather than an unbounded PyPI upgrade.

If Code Puppy is already installed, the installer reports that fact and leaves
its environment unchanged. Use `--skip-engine` when you explicitly want an
overlay-only refresh; both paths preserve the existing engine.

If a previous failed installation left a broken or partial pipx environment,
use `--repair-engine`. This is deliberately different from an upgrade: it uses
pipx `--force` only to replace the engine with the selected exact, checksummed
profile. It never asks PyPI for the newest Code Puppy release.

DroidPuppy is designed for Android devices running Termux.

Helpful tools already used by this bundle include:

- `am`
- `pm`
- `cmd`
- `termux-open`
- `termux-open-url`

Optional but strongly useful for browser control:

- `adb` from `android-tools`

Install it in Termux with:

```bash
pkg install android-tools
```

## Wireless ADB / browser control

If you want Android browser CDP control:

1. Enable **Developer options**
2. Enable **Wireless debugging**
3. Pair ADB from Termux
4. Use the CDP tools to probe and connect to browser targets

## Optional future upgrades

Some mobile-native capabilities may improve if you also install/configure:

- `termux-api`
- the Termux:API Android app

That can help unlock deeper clipboard, notification, and device integration later.
