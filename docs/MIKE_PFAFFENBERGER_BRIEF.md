# Brief for Mike Pfaffenberger

## One-line summary

DroidPuppy is an Android-native orchestration layer powered by Code Puppy: it
turns a Termux phone into an observable agent control plane for Android apps,
browsers, settings, workflows, and device actions.

## Why this exists

Code Puppy already provides the engine: agents, callbacks, plugins, tools,
model routing, and an operator loop.

DroidPuppy focuses on a specific environment where that engine can become more
valuable: Android.

Phones are not small desktops. Android has its own surfaces, constraints, and
control seams:

- intents
- settings panels
- share sheets
- app activities
- wireless ADB
- browser DevTools sockets
- screenshots and UI hierarchy
- app-specific business workflows

DroidPuppy turns those seams into a Code Puppy-compatible operating layer.

## What is implemented

DroidPuppy currently includes:

- Android app launching and settings routing
- browser handoff into Brave, Chrome, or system handlers
- wireless ADB and CDP readiness tooling
- browser page reading, link extraction, HTML inspection, clicking, input, and screenshots
- app inventory, process, logcat, dumpsys, and support-bundle tooling
- business workflow capture artifacts
- versioned contracts for intents, tasks, handoffs, observations, and results
- a runnable Orchestra Agent substrate with durable state and approval gates

## Architectural stance

DroidPuppy is intentionally plugin-first.

The goal is not to mutate Code Puppy into an Android product. The goal is to
respect Code Puppy's extension model and build the Android-native layer beside
it.

The boundary is:

- Code Puppy owns the general engine.
- DroidPuppy owns Android orchestration.
- Engine patches should stay small, tested, and upstream-reviewable.
- Product-layer experimentation belongs in DroidPuppy.

## Safety and governance

DroidPuppy treats orchestration as a control-plane problem, not a pile of tool
calls.

The Orchestra Agent work demonstrates:

- typed contracts
- durable execution state
- observable task progress
- adapter boundaries
- side-effect classification
- approval gates for irreversible actions
- recovery rules that do not blindly retry risky work

This matters because Android orchestration can cross from harmless reads into
real side effects quickly.

## What I want to demonstrate

This project is meant to show that I can:

- understand an existing engine and extend it cleanly
- keep repo ownership disciplined
- build around real platform constraints instead of pretending Android is Linux with a smaller keyboard
- document architecture and failure modes clearly
- write tests for safety and regression seams
- turn local experiments into a maintainable product layer

## Suggested evaluation path

1. Read `README.md`.
2. Read `docs/PORTFOLIO_KENNEL.md`.
3. Read `docs/PROJECT_OS_BRIEF.md`.
4. Read `docs/ORCHESTRA_AGENT.md` and `docs/ARCHITECTURE_REVIEW.md`.
5. Review `contracts/v1/`.
6. Run the demos in `orchestra/README.md`.
7. Inspect the Code Puppy branch commits for focused engine fixes.

## Near-term roadmap

The next useful milestones are:

1. clean repo separation between Code Puppy and DroidPuppy
2. one polished end-to-end Android workflow case study
3. CI or local scripts for schema validation and demo smoke tests
4. screenshots or terminal transcripts proving the Android workflows
5. clearer packaging/install instructions for Code Puppy users
6. upstream lean-install fixes so users can install Code Puppy, add the DroidPuppy overlay, and use it on Android the same day

## Closing statement

DroidPuppy is my attempt to build a serious extension layer around Code Puppy,
not a random fork. It is an Android-native orchestration product that uses Code
Puppy's plugin architecture as intended and pushes it into a practical mobile
control-plane use case.
