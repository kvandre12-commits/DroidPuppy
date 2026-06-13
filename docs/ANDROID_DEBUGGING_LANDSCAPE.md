# Android Debugging Landscape

DroidPuppy is staking out the Android-native debugging layer.

This document maps the territory DroidPuppy is meant to own.

## Core command surfaces

### adb
Android Debug Bridge is the backbone of Android debugging.

It enables:
- device connection and pairing
- shell access
- port forwarding
- file transfer
- log capture
- bugreports
- wireless debugging

### adb shell
Once inside the shell, Android exposes a rich debugging surface including:
- `am`
- `pm`
- `cmd`
- `dumpsys`
- `logcat`
- `getprop`
- `settings`
- `/proc` inspection

## Android intent and package control

### am
The Activity Manager command is central for:
- launching apps
- opening settings pages
- triggering Android intents
- mobile workflow routing

### pm
The Package Manager command is central for:
- package discovery
- app presence checks
- package-level inspection

## Logs and device state

### logcat
Android logs are essential for:
- crash diagnosis
- runtime errors
- app messages
- service behavior

### dumpsys
`dumpsys` exposes Android service state such as:
- activity state
- battery state
- package state
- memory
- graphics
- windows
- connectivity

## Browser debugging

### CDP / DevTools sockets
Chromium-family browsers on Android can expose DevTools sockets such as:
- `chrome_devtools_remote`

With wireless ADB and port forwarding, this enables:
- page inspection
- target listing
- JavaScript evaluation
- screenshots
- lightweight automation

## UI-level debugging and automation

### UI Automator
Android UI Automator is important for true app-level UI automation beyond browsers.

### input / hierarchy dump
Potential future DroidPuppy territory includes:
- tap and key injection
- text entry
- UI hierarchy dumping
- screen-state interpretation

## Performance and profiling

### Perfetto
Perfetto is Android's major tracing/profiling tool for deeper system and performance analysis.

### Other system diagnostics
Useful service-level tools include:
- `dumpsys meminfo`
- `dumpsys gfxinfo`
- `batterystats`
- `bugreport`

## DroidPuppy direction

DroidPuppy should grow into an Android-native agent operating layer with control over:

1. app launching and settings routing
2. logs and device service state
3. browser/CDP inspection and automation
4. mobile UI inspection and action
5. workflow orchestration across Android surfaces

## Immediate territory to claim

The first debugging territory DroidPuppy should own clearly:

- Android logs
- Android service inspection
- wireless ADB browser control
- friendly Android-native command routing

That is why the next plugin kits matter:
- `android_logcat_kit`
- `android_dumpsys_kit`
