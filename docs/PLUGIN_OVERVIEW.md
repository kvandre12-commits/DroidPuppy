# Plugin Overview

## android_brave_bridge
Purpose: browser launch and Android/Termux diagnostics.

Key tools:
- `android_brave_status`
- `android_browser_open_url`

## android_cdp_bridge
Purpose: wireless ADB and Chrome DevTools Protocol readiness.

Key tools:
- `android_cdp_doctor`
- `android_adb_wireless_helper`
- `android_cdp_probe`

## android_cdp_client
Purpose: direct browser control once CDP is reachable.

Key tools:
- `android_cdp_list_targets`
- `android_cdp_get_page_info`
- `android_cdp_navigate`
- `android_cdp_eval_js`

## android_browser_easy
Purpose: plain-language read helpers for pages.

Key tools:
- `android_browser_read_page`
- `android_browser_get_html`
- `android_browser_list_links`
- `android_browser_get_text_by_selector`

## android_browser_actions
Purpose: lightweight page actions.

Key tools:
- `android_browser_click_link_by_text`
- `android_browser_click_selector`
- `android_browser_fill_input`
- `android_browser_take_screenshot`

## android_utility_kit
Purpose: Droid-native helpers that still matter even without browser CDP.

Key tools:
- `android_utility_doctor`
- `android_open_settings`
- `android_launch_app`
- `android_share_text`
- `android_find_apps`

## android_friendly_router
Purpose: a friendlier front door to Android actions.

Key tools:
- `android_open`
- `android_list_shortcuts`

## droidpuppy_doctor
Purpose: a single master health check for the whole DroidPuppy stack.

Key tools:
- `droidpuppy_doctor`

It aggregates the lower-level `*_doctor`/`*_status` checks, verifies core Android
commands and browsers, optionally probes CDP, and inventories installed plugins.

## Overall shape

The stack is layered:

1. **Android utility / browser launch**
2. **Wireless ADB + CDP bridge**
3. **Direct CDP client**
4. **Plain-language read tools**
5. **Friendly action tools**

That layering keeps DroidPuppy useful in low-connectivity situations while still allowing deeper browser control when wireless debugging is available.
