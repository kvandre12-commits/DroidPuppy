# Portfolio Kennel

DroidPuppy is the portfolio project: an Android-native orchestration layer
powered by Code Puppy.

The purpose of this kennel is to make the work easy to evaluate. It separates
engine contributions, product-layer ownership, architectural proof, and next
steps so a reviewer can see disciplined engineering instead of a pile of local
experiments.

## Positioning

Code Puppy is the general-purpose agent engine.

DroidPuppy is the Android operating layer built around that engine:

- phone-first orchestration from Termux
- Android app, settings, browser, ADB, and CDP control surfaces
- workflow capture for real business processes
- contract-based orchestration through the Orchestra Agent
- approval-gated execution for risky or irreversible actions
- observable state, handoffs, results, and support bundles

The resume sentence:

> Built DroidPuppy, an Android-native orchestration layer powered by Code Puppy,
> turning a Termux phone into an observable, approval-gated agent control plane
> for apps, browsers, settings, workflows, and device actions.

## Repository ownership

### Code Puppy

Code Puppy owns engine-level work:

- plugin and callback fixes
- model/auth provider improvements
- Android/Termux compatibility patches
- generic tool registration and integration seams
- tests suitable for upstream review

Current local branch used for this work:

```text
code_puppy / droidpuppy
```

### DroidPuppy

DroidPuppy owns the Android orchestration product layer:

- Android plugins and tool families
- Droid-native setup and doctor workflows
- app capability audits
- business workflow captures
- contracts and Orchestra Agent demos
- architecture, roadmap, case studies, and operator docs

Primary branch:

```text
DroidPuppy / main
```

## Evidence map

| Evidence | Where | What it proves |
|---|---|---|
| Plugin bundle | `code_puppy/plugins/` | Code Puppy-compatible extension layer |
| Android doctor | `droidpuppy_doctor` plugin | Platform health checks and guided setup |
| Browser/CDP tools | Android browser and CDP plugins | On-device web control without desktop assumptions |
| Contracts | `contracts/v1/` | Versioned handoff and task/result schemas |
| Orchestra Agent | `orchestra/` | Durable, resumable, approval-aware orchestration |
| Business workflows | `docs/business_workflows/` | Practical workflow capture, not toy demos |
| Architecture docs | `docs/ORCHESTRA_AGENT.md`, `docs/ARCHITECTURE_REVIEW.md` | Principal-level system boundaries and failure-mode thinking |
| Plugin reference | `docs/PLUGIN_REFERENCE.md` | Discoverability and operator usability |

## Demonstration path

A reviewer should be able to evaluate DroidPuppy in this order:

1. Read `README.md` for the product framing.
2. Read `docs/VISION.md` for the platform direction.
3. Read `docs/ORCHESTRA_AGENT.md` for the system contract.
4. Read `docs/ARCHITECTURE_REVIEW.md` for failure modes and design discipline.
5. Run the Orchestra demos from `orchestra/README.md`.
6. Review `docs/business_workflows/` for real workflow modeling.
7. Inspect Code Puppy commits for upstream-quality engine patches.

## Distinguished-engineer signals

DroidPuppy should demonstrate these qualities:

- clear repo boundaries
- plugin-first architecture
- small, reviewable commits
- explicit contracts and schemas
- human approval for risky actions
- durable state and recovery thinking
- Android-native constraints handled directly
- docs that explain both why and how
- tests for regressions and safety seams

## What not to do

Do not turn Code Puppy into a personal product fork.

Do not put DroidPuppy product docs into Code Puppy core.

Do not mix trading, Android orchestration, and generic engine changes in one
commit.

Do not ship untracked experiments as if they were architecture.

Do not force desktop assumptions onto Android. If Termux has a native package,
use it before trying to build Rust wheels on-device.

## Near-term polish plan

1. Keep `DroidPuppy/` ignored or clearly separate from the Code Puppy root repo.
2. Commit DroidPuppy business workflow docs in the DroidPuppy repo.
3. Add a short case study showing one end-to-end Android workflow.
4. Keep Code Puppy commits focused and upstream-reviewable.
5. Add screenshots or terminal transcripts for doctor and demo commands.
6. Maintain a changelog that separates engine patches from DroidPuppy product work.

## Reviewer takeaway

The goal is not to look like a person who forked an engine and got lost.

The goal is to look like a platform engineer who:

- understood the engine,
- respected its extension model,
- found a real environment where it needed a native layer,
- built that layer with contracts, safety, docs, and tests,
- and can keep repo boundaries clean while doing it.
