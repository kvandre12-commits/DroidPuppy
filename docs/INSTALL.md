# Installation

## Goal

DroidPuppy is meant to layer on top of **Mike's upstream Code Puppy install**
without editing site-packages or mutating the upstream checkout.

The preferred install target is Code Puppy's **user plugin tier**:

```text
~/.code_puppy/plugins/
```

That works whether Code Puppy came from `uvx`, `pip`, or a git checkout.

## Basic install

1. Install Code Puppy from upstream.
2. Clone this repo.
3. Run:

```bash
python scripts/install_overlay.py
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

### Verify the stack after install

Start Code Puppy, then run the DroidPuppy doctor tool to check platform,
Android commands, browser availability, optional ADB/CDP readiness, and plugin
inventory.

## Termux notes

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
