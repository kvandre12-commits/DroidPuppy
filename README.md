# DroidPuppy

**An Android-native agent operating layer for Code Puppy.**

DroidPuppy is a focused plugin bundle for making Code Puppy feel at home on Android.
It is the beginning of an **Android-native agent operating layer**: a phone-first control surface for apps, settings, browsers, workflows, and agent-driven mobile actions.
It turns a phone running Termux into a more capable mobile workstation with:

- Android app launching and settings routing
- Brave and Chrome handoff from Termux
- wireless ADB and CDP browser bridging
- live browser inspection and lightweight automation
- plain-language page reading, link extraction, screenshots, and friendly shortcuts

## Why DroidPuppy exists

Code Puppy can run on a phone, but DroidPuppy is about making it **feel native there**.

Instead of treating Android like a cramped desktop, this repo leans into mobile reality:

- open apps and settings directly
- work with Brave and Chrome from the phone itself
- recover useful browser control through Android CDP
- expose simple tools that do not require deep browser-engine knowledge

## What is in this repo?

This repo is packaged as a Code Puppy-compatible overlay:

```text
code_puppy/plugins/
```

Each folder under `code_puppy/plugins/` is a plugin that can be copied into a Code Puppy checkout.

## Included plugin families

### `android_brave_bridge`
Launches URLs in Brave or Chrome and reports Android browser-launch capability.

### `android_cdp_bridge`
Helps pair wireless ADB, probe DevTools sockets, and verify Android CDP readiness.

### `android_cdp_client`
Provides live CDP target listing, navigation, page inspection, and JavaScript evaluation.

### `android_browser_easy`
Wraps lower-level browser control in plain-language helpers like reading page text, links, and HTML.

### `android_browser_actions`
Adds action-oriented helpers like click, fill input, and screenshot capture.

### `android_utility_kit`
Adds Droid-native utilities such as app launching, settings routing, text sharing, and capability inspection.

### `android_friendly_router`
Adds a friendly front door so you can think in commands like:

- `open brave`
- `open wifi`
- `open developer options`
- `open https://example.com`

## Quick start

1. Clone or copy this repo.
2. Copy the plugin folders into a Code Puppy checkout under:

```text
code_puppy/plugins/
```

3. Start using the Android-focused tools from Code Puppy.

For a fuller setup guide, see:

- [`docs/INSTALL.md`](docs/INSTALL.md)
- [`docs/PLUGIN_OVERVIEW.md`](docs/PLUGIN_OVERVIEW.md)
- [`docs/DEVELOPER_TOOLS.md`](docs/DEVELOPER_TOOLS.md)

## Highlights

- Open Brave or Chrome from Termux
- Open Android settings pages by friendly name
- Pair wireless ADB from the phone itself
- Reach live browser CDP endpoints on Android
- Read page text, links, and HTML without raw CDP knowledge
- Click links, fill inputs, and capture screenshots

## Notes

- Some browser-control features depend on Android wireless debugging and local network access.
- Some extra mobile integrations may benefit from `termux-api` later.
- DroidPuppy is intentionally plugin-first so it stays aligned with Code Puppy architecture.
