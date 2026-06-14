# DroidPuppy Command Cheatsheet

This file is a phone-friendly command reference for working inside the `DroidPuppy` repo from Termux.

## Go to the repo

```bash
cd ~/code_puppy/DroidPuppy
```

## Check repo state

```bash
git status
```

Short version:

```bash
git status --short
```

## See recent commits

```bash
git log --oneline -n 5
```

## Push a normal change

```bash
cd ~/code_puppy/DroidPuppy
git add .
git commit -m "Your commit message here"
git push
```

## Important Git rule

If your commit message has spaces, always wrap it in quotes:

```bash
git commit -m "Add Android screen capture kit"
```

Not:

```bash
git commit -m Add Android screen capture kit
```

## Stage only specific paths

Example:

```bash
git add README.md docs/VISION.md code_puppy/plugins/android_input_kit
```

## Reconnect wireless ADB

If the phone is back on Wi-Fi and still paired:

```bash
adb connect IP:PORT
adb devices -l
```

If the device is stuck offline:

```bash
adb reconnect offline
adb devices -l
```

## Full wireless ADB pairing flow

```bash
adb pair IP:PAIR_PORT PAIR_CODE
adb connect IP:CONNECT_PORT
adb devices -l
```

## Open GitHub repo page

```bash
termux-open-url https://github.com/kvandre12-commits/DroidPuppy
```

## Quick Android checks

Open Wi-Fi settings:

```bash
am start -a android.settings.WIFI_SETTINGS
```

Open Developer Options:

```bash
am start -a android.settings.APPLICATION_DEVELOPMENT_SETTINGS
```

Launch Brave:

```bash
am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p com.brave.browser
```

## If Git says "nothing to commit"

That usually means one of these is true:
- your changes were already committed
- you forgot to edit/save files
- you are in the wrong folder

Check with:

```bash
pwd
git status
git log --oneline -n 3
```

## If Git says you are up to date

That usually means the push already worked.

Check with:

```bash
git log --oneline -n 3
```

## Safest phone workflow

```bash
cd ~/code_puppy/DroidPuppy
git status --short
git add .
git status --short
git commit -m "Describe what you built"
git push
```
