# Upstream Engine and Overlay

## Short version

Code Puppy is the engine.

DroidPuppy is the Android-native overlay.

That split is intentional. It keeps Mike's upstream repo lean while letting us
ship the phone-native product layer quickly through Code Puppy's existing plugin
contract.

## Why this document exists

We do **not** want to keep bothering upstream with every DroidPuppy product
change, README flourish, or Android workflow experiment.

We **do** want a clean same-day path where someone can:

1. install upstream Code Puppy
2. clone DroidPuppy
3. run `python scripts/install_overlay.py`
4. use the Android stack from Code Puppy's supported plugin tiers

## What belongs upstream Code Puppy

Upstream should own the reusable engine layer:

- agent runtime
- plugin loading
- optional dependency hygiene
- graceful imports/fallbacks
- generic callbacks and tool seams
- docs about core installation and extras

Code Puppy is already the open-source, privacy-respecting core that makes the
whole stack possible. DroidPuppy should benefit from that, not duplicate it.

## What belongs in DroidPuppy

DroidPuppy should own the Android product layer:

- Android app/settings/browser tooling
- ADB and CDP helpers
- Droid-native doctors and setup flows
- workflow capture and support bundles
- Project OS operator docs
- product positioning for the phone-native experience

## Why the light installer matters

`scripts/install_overlay.py` is the light installer.

It exists so we can ship DroidPuppy through the plugin tiers Code Puppy already
supports instead of mutating site-packages, vendoring a fork, or turning
upstream into our personal junk drawer.

That gives us the clean contract we want:

```text
upstream Code Puppy install
    +
DroidPuppy overlay install
    =
same-day Android operator stack
```

## Project OS angle

Project OS is the larger doctrine: the project is a system spread across repos,
agents, contracts, tools, and device surfaces.

In that frame:

- Code Puppy proves the engine
- DroidPuppy proves the Android-native operating layer
- the light installer proves the two can connect cleanly without repo sprawl

## Takeaway

If a change is primarily about Android product behavior, installer UX, Project
OS framing, or phone-native operator workflows, it should usually land in
DroidPuppy first.

If a change improves the general engine for everyone, that is the upstream lane.
