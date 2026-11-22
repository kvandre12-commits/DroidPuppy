# Protected June Brave Baseline

The architectural rationale is documented in
[Platform Substitution Thesis](PLATFORM_SUBSTITUTION_THESIS.md).

`june-brave-v1` preserves the Android porting boundary first committed in
DroidPuppy on 2026-06-13 (`275bd5a8`). It is intentionally narrower than the
`android-0720` recovery profile.

## Contract

The baseline does exactly one thing: layer the original seven Android actuator
plugins onto an **existing, working Code Puppy engine**.

```text
working Code Puppy engine
        +
seven Android overlay plugins
        +
Brave intent handoff
```

It does not install, repair, upgrade, or synchronize an engine. It installs no
Python packages and no Termux build tools. In particular, the baseline must not
introduce:

- `pydantic-ai-pax` or an upstream Pydantic AI checkout;
- `pydantic-ai-harness` or Monty;
- Playwright/desktop Chromium;
- Tree-sitter language bundles;
- broad `uv sync --all-groups` behavior.

The machine-readable contract is
[`baselines/june-brave-v1.json`](../baselines/june-brave-v1.json). The installer
embeds its SHA-256 and refuses a changed manifest. The manifest also freezes a
deterministic tree hash for each allowed plugin, so keeping a familiar folder
name while replacing its implementation fails verification. The stdlib-only
verifier checks the protected policy, plugin allowlist, and implementation
hashes without importing Code Puppy:

```bash
python scripts/verify_baseline.py june-brave-v1
```

## Original plugin allowlist

- `android_brave_bridge`
- `android_browser_actions`
- `android_browser_easy`
- `android_cdp_bridge`
- `android_cdp_client`
- `android_friendly_router`
- `android_utility_kit`

Base browser behavior is Android intent handoff to native Brave. ADB/CDP is an
advanced capability already represented in the original toolkit, not a reason
to install desktop Playwright.

## Install or preview

A working `code-puppy` must already be on `PATH`.

```bash
bash install.sh --dry-run --baseline june-brave-v1
bash install.sh --baseline june-brave-v1
```

The baseline deliberately fails when no engine exists. Use `android-0720` only
when a fresh engine recovery is actually required; that is a separate, heavier
operation with its own validated constraints.

## Change control

Do not silently expand this baseline. A change to its plugin list, package
policy, forbidden operations, or provenance requires:

1. a new baseline ID;
2. a new manifest and checksum;
3. explicit tests proving the old baseline remains unchanged;
4. Android evidence for the new baseline.

Implementation fixes require a new baseline ID. Dependencies and capabilities
do not get smuggled into `june-brave-v1` wearing a fashionable framework hat.
