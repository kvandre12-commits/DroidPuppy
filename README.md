# DroidPuppy

DroidPuppy is an Android-first toolkit for Code Puppy.

It packages mobile-native plugins for:
- Android app launching and settings routing
- Brave/Chrome browser handoff from Termux
- wireless ADB/CDP browser bridging
- live browser inspection and automation on Android
- simple page reading, link extraction, screenshots, and friendly commands

## What is in this bundle?

This repo is structured as a Code Puppy-compatible overlay:

```text
code_puppy/plugins/
```

The plugins here are designed to drop into a Code Puppy checkout while keeping
plugin-first architecture intact.

## Included plugin families

- `android_brave_bridge`
- `android_cdp_bridge`
- `android_cdp_client`
- `android_browser_easy`
- `android_browser_actions`
- `android_utility_kit`
- `android_friendly_router`

## Installation

Copy the plugin directories under:

```text
code_puppy/plugins/
```

into a Code Puppy repo or compare/merge them into an Android-focused branch.

## Highlights

- Open Brave or Chrome from Termux
- Pair wireless ADB and probe Android CDP sockets
- Read live browser targets and evaluate JavaScript
- Read page text, links, and HTML in plain language
- Take screenshots and click/fill page elements
- Open friendly Android targets like `wifi`, `developer options`, or `brave`

## Notes

- Some features depend on Android wireless debugging and local network access.
- Some Droid-native enhancements such as clipboard and notifications may need
  `termux-api` tools if you want deeper Termux integration later.
