# Installation

## Goal

DroidPuppy is meant to be copied into a Code Puppy checkout as a plugin overlay.

## Basic install

Copy the plugin directories from this repo into:

```text
code_puppy/plugins/
```

inside your Code Puppy repo.

The included plugin folders are:

- `android_brave_bridge`
- `android_cdp_bridge`
- `android_cdp_client`
- `android_browser_easy`
- `android_browser_actions`
- `android_utility_kit`
- `android_friendly_router`

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
