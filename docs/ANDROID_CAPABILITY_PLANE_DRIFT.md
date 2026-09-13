# Android Capability-Plane Drift

**Status:** Confirmed engineering finding — architectural debt (not a version regression).
**Scope:** Code Puppy Android (Termux) runtime; agents `web-retriever` and `qa-kitten`; DroidPuppy Android providers.
**Method:** Read-only. Static source review + in-process introspection on code-puppy `0.0.720`; git/`gh` history on the code_puppy fork and DroidPuppy repo. No runtime code modified, nothing installed, no additional agents inspected.

## Invariant (violated)

```
advertised capability ⊆ resolved executable capability
```

This is stronger than "the advertised tool name exists somewhere." A tool whose advertised
semantics have no executable provider on the platform still violates the invariant.

---

## Observed facts

### 1. Runtime measurement — code-puppy `0.0.720`, `sys.platform == "android"`

Resolved in-process (isolated HOME/XDG sandbox): imported `code_puppy.tools.TOOL_REGISTRY`,
instantiated each agent, diffed `get_available_tools()` against the live registry.

- Registered tool universe: **16** tools. `browser_*` registered: **0**. `android`/`cdp`/`droid` registered: **0**.
- `web-retriever`: advertises **50** tools → **7** resolve (bound to the model) → **43** silently skipped (every `browser_*`).
  - Resolved: `load_image_for_analysis, list_files, read_file, grep, create_file, replace_in_file, ask_user_question`.
- `qa-kitten`: advertises **44** tools → **1** resolves (`load_image_for_analysis`) → **43** silently skipped (every `browser_*`).
- Skip mechanism: `register_tools_for_agent` (`code_puppy/tools/__init__.py`) — a tool name not in
  `TOOL_REGISTRY` triggers `emit_warning("Unknown tool '<name>' requested, skipping...")` then `continue`.
  The tool is never bound to the model.
- The agents' system prompts and descriptions are static strings, **not** filtered by the registry.
  Both still identify as "powered by Playwright" and instruct the model to call `browser_initialize`,
  `browser_navigate`, etc. (`qa-kitten` even instructs `headless=True` "for production").

### 2. Android registry gate

- `code_puppy/tools/__init__.py`: `_load_browser_tool_registry()` returns `{}` when
  `sys.platform == "android"`, otherwise returns `BROWSER_TOOL_REGISTRY`.
- Stock browser backend is Playwright: `code_puppy/tools/browser/browser_manager.py` has a top-level
  `from playwright.async_api import ...`; browser launch is `chromium.launch_persistent_context(..., headless=self.headless)`;
  `self.headless` defaults to `True` (`BROWSER_HEADLESS`). Playwright is not installed in the examined venv.

### 3. DroidPuppy provider namespace (separate)

- DroidPuppy providers register their own names (`android_cdp_*`, `android_brave_*`, `android_ui_*`,
  `android_screen_capture_*`, ...), never `browser_*`.
- Neither agent's `get_available_tools()` references any `android_*` name. The plugin merge path unions
  plugin tools in **by name**; it cannot alias `browser_navigate` → an `android_*` provider.
- Consequence: DroidPuppy capabilities are **not substituted** into the advertised `browser_*` surface;
  they exist on an independent naming plane.

### 4. Historical provenance (code_puppy fork tags; DroidPuppy repo)

| Date | Commit | First version containing | Event |
|------|--------|--------------------------|-------|
| 2025-09-25 | `7738b9e6` | v0.0.484 | `qa-kitten` created; already advertises 39 `browser_*` tools; never platform-aware. |
| 2026-06-13 | `275bd5a8` (DroidPuppy) | — | "Initial DroidPuppy Android toolkit": `android_cdp_bridge` + `android_brave_bridge` providers born on a separate namespace. |
| 2026-08-04 | `4e5705ad` | v0.0.681 | `web-retriever` created; advertises ~50 `browser_*` tools; never platform-aware. |
| 2026-08-09 | `138ffbbd` | v0.0.690 | "Exclude Playwright on Android (#718)": adds the `sys.platform == "android"` gate; empties the browser registry on Android; Code Puppy becomes runnable without Playwright. |

Supporting evidence:

- `v0.0.574`: `tools/__init__.py` had **7** unconditional `from code_puppy.tools.browser ...` imports and
  **0** android gates; `browser_manager.py:13` was a top-level `from playwright.async_api import ...`.
  Therefore **`.574`'s stock Playwright-backed browser/tool import path was incompatible with the examined
  Android environment** (import-time failure on that path). `qa-kitten` at `.574` already advertised 39
  `browser_*` tools.
- `git log -S 'sys.platform'` over both agent files is empty across all history — the advertised tool lists
  were **never** guarded by platform.

---

## Classification

**Architectural debt, not a version regression.** No revision ever satisfied the invariant on Android:

- **≤ v0.0.690:** the stock Playwright-backed browser/tool import path was incompatible with the examined
  Android environment; the agents advertised `browser_*` tools regardless. The surfaces were never
  reconciled — both were broken.
- **≥ v0.0.690:** Android is runnable **because** the browser tools are removed from the registry; the
  static agent advertisements were not reconciled afterward, producing capability-plane drift.

No prior reconciliation existed to be removed. The `.690` change did not break browser automation; it
stopped an existing incompatibility from failing at import time by removing the Playwright browser tools on
Android. What was not done is reconciling the agents' advertisements to the reduced capability set.

---

## Implications (not evidence; no fix implemented or proposed here)

- A model can follow its prompt correctly and still produce behavior that is wrong for the actual runtime
  capability set. A stronger model may try harder to invoke tools that do not exist on the platform.
- Because DroidPuppy solves Android browser/device control on a separate namespace, installing it does not,
  by itself, repair the agents' `browser_*` promises.
- `browser_find_by_role` (semantic) and an Android coordinate tap are not equivalent operations; a
  reconciliation must be allowed to report a capability as **unavailable** rather than pretend equivalence.
- Reconciling the invariant is a capability-resolution concern (intent → capability → platform-appropriate
  provider, or explicit "unavailable"), not an alias table. **Deliberately out of scope for this finding.**
