# DroidPuppy Plugin Reference

> Auto-generated inventory of every DroidPuppy plugin and its tools.
> Last generated: 2026-06-20. Regenerate with `python scripts/gen_plugin_reference.py`.
> Descriptions marked _(derived)_ were synthesized from the tool name (the source had no docstring — a good first contribution target).

**37 plugins · 126 tools**

## Index

- [`android_app_doctor_kit`](#android-app-doctor-kit) — Register the Android App Doctor tool. (1 tools)
- [`android_app_inventory_kit`](#android-app-inventory-kit) — Register Android app inventory and profiling tools. (3 tools)
- [`android_app_stack_report_kit`](#android-app-stack-report-kit) — Register app stack reporting tools. (3 tools)
- [`android_app_workflow_kit`](#android-app-workflow-kit) — Register named cross-app workflow tools. (3 tools)
- [`android_brave_bridge`](#android-brave-bridge) — Register Android Brave bridge tools. (2 tools)
- [`android_browser_actions`](#android-browser-actions) — Register Android browser action tools. (4 tools)
- [`android_browser_easy`](#android-browser-easy) — Register simple Android browser helper tools. (4 tools)
- [`android_bugreport_kit`](#android-bugreport-kit) — Register Android bugreport kit tools. (2 tools)
- [`android_business_workflow_capture_kit`](#android-business-workflow-capture-kit) — Register business workflow capture tools. (4 tools)
- [`android_cdp_bridge`](#android-cdp-bridge) — Register Android CDP bridge tools. (3 tools)
- [`android_cdp_client`](#android-cdp-client) — Register Android CDP client tools. (4 tools)
- [`android_dumpsys_kit`](#android-dumpsys-kit) — Register Android dumpsys kit tools. (3 tools)
- [`android_edge_kit`](#android-edge-kit) — Register DroidPuppy 'edge' element-testing tools. (2 tools)
- [`android_eyes_inbox_kit`](#android-eyes-inbox-kit) — Register Android eyes inbox tools. (8 tools)
- [`android_eyes_worker_kit`](#android-eyes-worker-kit) — Register Android eyes worker tools. (7 tools)
- [`android_friendly_router`](#android-friendly-router) — Register friendly Android router tools. (2 tools)
- [`android_handoff_kit`](#android-handoff-kit) — Register Android handoff tools. (5 tools)
- [`android_input_kit`](#android-input-kit) — Register Android input kit tools. (6 tools)
- [`android_intent_audit_kit`](#android-intent-audit-kit) — Register intent auditing tools. (4 tools)
- [`android_intent_kit`](#android-intent-kit) — Register structured Android intent tools. (4 tools)
- [`android_logcat_kit`](#android-logcat-kit) — Register Android logcat kit tools. (3 tools)
- [`android_notification_kit`](#android-notification-kit) — Register Android notification kit tools. (4 tools)
- [`android_orchestration_blueprint_kit`](#android-orchestration-blueprint-kit) — Register orchestration blueprint tools. (3 tools)
- [`android_process_kit`](#android-process-kit) — Register Android process kit tools. (3 tools)
- [`android_reconnect_helper`](#android-reconnect-helper) — Register wireless ADB reconnect helper tools. (4 tools)
- [`android_screen_capture_kit`](#android-screen-capture-kit) — Register Android screen capture kit tools. (3 tools)
- [`android_setup_helper`](#android-setup-helper) — Register friendly setup helper tools. (3 tools)
- [`android_support_bundle_kit`](#android-support-bundle-kit) — Register DroidPuppy support bundle tools. (3 tools)
- [`android_support_share_wizard`](#android-support-share-wizard) — Register support bundle sharing and issue-draft tools. (4 tools)
- [`android_tutorial_nudges`](#android-tutorial-nudges) — Tutorial nudges that surface the next helpful step after first use. (0 tools)
- [`android_ui_action_kit`](#android-ui-action-kit) — Register Android UI action kit tools. (3 tools)
- [`android_ui_capability_audit_kit`](#android-ui-capability-audit-kit) — Register UI capability audit tools. (4 tools)
- [`android_ui_dump_kit`](#android-ui-dump-kit) — Register Android UI dump kit tools. (3 tools)
- [`android_utility_kit`](#android-utility-kit) — Register Android utility kit tools. (5 tools)
- [`android_workflow_feasibility_kit`](#android-workflow-feasibility-kit) — Register workflow feasibility assessment tools. (3 tools)
- [`android_workflow_macro_kit`](#android-workflow-macro-kit) — Register Android workflow macro tools. (3 tools)
- [`droidpuppy_doctor`](#droidpuppy-doctor) — Register the DroidPuppy master doctor tool. (1 tools)

---

## android_app_doctor_kit

Register the Android App Doctor tool.

| Tool | Description |
|------|-------------|
| `android_app_doctor` | Diagnose misbehaving apps from logcat (or pasted ``log_text``). |

## android_app_inventory_kit

Register Android app inventory and profiling tools.

| Tool | Description |
|------|-------------|
| `android_app_inventory_doctor` | App inventory doctor _(derived)_ |
| `android_app_inventory_list` | App inventory list _(derived)_ |
| `android_app_profile` | App profile _(derived)_ |

## android_app_stack_report_kit

Register app stack reporting tools.

| Tool | Description |
|------|-------------|
| `android_app_stack_report_doctor` | App stack report doctor _(derived)_ |
| `android_app_stack_report_generate` | App stack report generate _(derived)_ |
| `android_app_stack_report_examples` | App stack report examples _(derived)_ |

## android_app_workflow_kit

Register named cross-app workflow tools.

| Tool | Description |
|------|-------------|
| `android_app_workflow_doctor` | App workflow doctor _(derived)_ |
| `android_app_workflow_list` | App workflow list _(derived)_ |
| `android_app_workflow_run` | App workflow run _(derived)_ |

## android_brave_bridge

Register Android Brave bridge tools.

| Tool | Description |
|------|-------------|
| `android_brave_status` | Inspect Android/Termux browser-launch capability. |
| `android_browser_open_url` | Open a URL in Brave, Chrome, or the Android system browser handler. |

## android_browser_actions

Register Android browser action tools.

| Tool | Description |
|------|-------------|
| `android_browser_click_link_by_text` | Click a link or button by visible text. |
| `android_browser_click_selector` | Click the first element matching a CSS selector. |
| `android_browser_fill_input` | Fill an input field by CSS selector. |
| `android_browser_take_screenshot` | Capture a screenshot of the selected browser page. |

## android_browser_easy

Register simple Android browser helper tools.

| Tool | Description |
|------|-------------|
| `android_browser_read_page` | Read a page in plain language: title, URL, visible text, headings, link count. |
| `android_browser_get_html` | Get raw HTML for the page or for one CSS-selected element. |
| `android_browser_list_links` | List links on a page with text and href values. |
| `android_browser_get_text_by_selector` | Get text from one or more elements matched by a CSS selector. |

## android_bugreport_kit

Register Android bugreport kit tools.

| Tool | Description |
|------|-------------|
| `android_bugreport_doctor` | Bugreport doctor _(derived)_ |
| `android_bugreport_collect` | Bugreport collect _(derived)_ |

## android_business_workflow_capture_kit

Register business workflow capture tools.

| Tool | Description |
|------|-------------|
| `android_business_workflow_capture_doctor` | Business workflow capture doctor _(derived)_ |
| `android_business_workflow_capture_template` | Business workflow capture template _(derived)_ |
| `android_business_workflow_capture_create` | Business workflow capture create _(derived)_ |
| `android_business_workflow_capture_examples` | Business workflow capture examples _(derived)_ |

## android_cdp_bridge

Register Android CDP bridge tools.

| Tool | Description |
|------|-------------|
| `android_cdp_doctor` | Inspect Android/Termux ADB/CDP readiness for on-device browser control. |
| `android_adb_wireless_helper` | Build or run adb pair/connect commands for Android wireless debugging. |
| `android_cdp_probe` | Probe Android browser DevTools sockets through adb port forwarding. |

## android_cdp_client

Register Android CDP client tools.

| Tool | Description |
|------|-------------|
| `android_cdp_list_targets` | List live CDP targets/tabs reachable through the Android CDP bridge. |
| `android_cdp_get_page_info` | Get title/url/readiness/basic HTML size for a CDP page target. |
| `android_cdp_navigate` | Navigate a selected CDP page target to a new URL. |
| `android_cdp_eval_js` | Evaluate JavaScript in a selected CDP page target. |

## android_dumpsys_kit

Register Android dumpsys kit tools.

| Tool | Description |
|------|-------------|
| `android_dumpsys_doctor` | Dumpsys doctor _(derived)_ |
| `android_dumpsys_service` | Dumpsys service _(derived)_ |
| `android_dumpsys_snapshot` | Dumpsys snapshot _(derived)_ |

## android_edge_kit

Register DroidPuppy 'edge' element-testing tools.

| Tool | Description |
|------|-------------|
| `android_edge_test_element` | Test a CSS selector on a live page: existence, count, text, attrs, geometry, visibility. |
| `android_edge_assert_text` | Assert the first element matching a selector contains expected text; returns passed + actual. |

## android_eyes_inbox_kit

Register Android eyes inbox tools.

| Tool | Description |
|------|-------------|
| `android_eyes_inbox_doctor` | Inspect local eyes inbox readiness and optional scanner availability. |
| `android_eyes_inbox_init` | Create the local eyes inbox folder layout. |
| `android_eyes_inbox_status` | Report file counts for the local eyes inbox. |
| `android_eyes_inbox_drop_text` | Write plain text directly into the eyes inbox as a note. |
| `android_eyes_inbox_drop_url` | Write a URL and optional note into the eyes inbox for later review. |
| `android_eyes_inbox_stage_file` | Copy or move an existing local file into the eyes inbox. |
| `android_eyes_inbox_scan` | Run the repo-local eyes inbox intake worker when available. |
| `android_eyes_inbox_examples` | Show example calls for the Android eyes inbox helpers. |

## android_eyes_worker_kit

Register Android eyes worker tools.

| Tool | Description |
|------|-------------|
| `android_eyes_worker_doctor` | Inspect eyes worker readiness, scripts, and scheduler capability. |
| `android_eyes_worker_status` | Run the local queue worker status command and return its JSON output. |
| `android_eyes_worker_run_once` | Run one short-lived worker pass, optionally scanning inbox first. |
| `android_eyes_worker_schedule` | Create a Termux scheduler wrapper for the eyes worker tick. |
| `android_eyes_worker_list_jobs` | List pending Termux scheduler jobs. |
| `android_eyes_worker_cancel_job` | Cancel one scheduled eyes worker job by Termux job id. |
| `android_eyes_worker_examples` | Show example calls for the eyes worker and scheduler helpers. |

## android_friendly_router

Register friendly Android router tools.

| Tool | Description |
|------|-------------|
| `android_open` | Open a friendly Android target like brave, wifi, developer options, or an https URL. |
| `android_list_shortcuts` | List built-in friendly Android shortcuts and examples. |

## android_handoff_kit

Register Android handoff tools.

| Tool | Description |
|------|-------------|
| `android_handoff_doctor` | Handoff doctor _(derived)_ |
| `android_handoff_text` | Handoff text _(derived)_ |
| `android_handoff_url` | Handoff url _(derived)_ |
| `android_handoff_file` | Handoff file _(derived)_ |
| `android_handoff_examples` | Handoff examples _(derived)_ |

## android_input_kit

Register Android input kit tools.

| Tool | Description |
|------|-------------|
| `android_input_doctor` | Input doctor _(derived)_ |
| `android_input_tap` | Input tap _(derived)_ |
| `android_input_tap_bounds` | Input tap bounds _(derived)_ |
| `android_input_swipe` | Input swipe _(derived)_ |
| `android_input_text` | Input text _(derived)_ |
| `android_input_keyevent` | Input keyevent _(derived)_ |

## android_intent_audit_kit

Register intent auditing tools.

| Tool | Description |
|------|-------------|
| `android_intent_audit_doctor` | Intent audit doctor _(derived)_ |
| `android_intent_audit_app` | Intent audit app _(derived)_ |
| `android_intent_audit_stack` | Intent audit stack _(derived)_ |
| `android_intent_audit_examples` | Intent audit examples _(derived)_ |

## android_intent_kit

Register structured Android intent tools.

| Tool | Description |
|------|-------------|
| `android_intent_doctor` | Intent doctor _(derived)_ |
| `android_intent_build` | Intent build _(derived)_ |
| `android_intent_send` | Intent send _(derived)_ |
| `android_intent_examples` | Intent examples _(derived)_ |

## android_logcat_kit

Register Android logcat kit tools.

| Tool | Description |
|------|-------------|
| `android_logcat_doctor` | Logcat doctor _(derived)_ |
| `android_logcat_recent` | Logcat recent _(derived)_ |
| `android_logcat_clear` | Logcat clear _(derived)_ |

## android_notification_kit

Register Android notification kit tools.

| Tool | Description |
|------|-------------|
| `android_notification_doctor` | Notification doctor _(derived)_ |
| `android_open_notification_settings` | Open notification settings _(derived)_ |
| `android_notification_setup_guide` | Notification setup guide _(derived)_ |
| `android_notification_send` | Notification send _(derived)_ |

## android_orchestration_blueprint_kit

Register orchestration blueprint tools.

| Tool | Description |
|------|-------------|
| `android_orchestration_blueprint_doctor` | Orchestration blueprint doctor _(derived)_ |
| `android_orchestration_blueprint_plan` | Orchestration blueprint plan _(derived)_ |
| `android_orchestration_blueprint_examples` | Orchestration blueprint examples _(derived)_ |

## android_process_kit

Register Android process kit tools.

| Tool | Description |
|------|-------------|
| `android_process_doctor` | Process doctor _(derived)_ |
| `android_process_list` | Process list _(derived)_ |
| `android_top_snapshot` | Top snapshot _(derived)_ |

## android_reconnect_helper

Register wireless ADB reconnect helper tools.

| Tool | Description |
|------|-------------|
| `android_reconnect_doctor` | Reconnect doctor _(derived)_ |
| `android_reconnect_plan` | Reconnect plan _(derived)_ |
| `android_reconnect_quick` | Reconnect quick _(derived)_ |
| `android_reconnect_full` | Reconnect full _(derived)_ |

## android_screen_capture_kit

Register Android screen capture kit tools.

| Tool | Description |
|------|-------------|
| `android_screen_capture_doctor` | Screen capture doctor _(derived)_ |
| `android_capture_screenshot` | Capture screenshot _(derived)_ |
| `android_record_screen` | Record screen _(derived)_ |

## android_setup_helper

Register friendly setup helper tools.

| Tool | Description |
|------|-------------|
| `android_setup_doctor` | Setup doctor _(derived)_ |
| `android_setup_next_steps` | Setup next steps _(derived)_ |
| `android_first_run_tour` | First run tour _(derived)_ |

## android_support_bundle_kit

Register DroidPuppy support bundle tools.

| Tool | Description |
|------|-------------|
| `android_support_bundle_doctor` | Support bundle doctor _(derived)_ |
| `android_support_bundle_plan` | Support bundle plan _(derived)_ |
| `android_support_bundle_collect` | Support bundle collect _(derived)_ |

## android_support_share_wizard

Register support bundle sharing and issue-draft tools.

| Tool | Description |
|------|-------------|
| `android_support_bundle_list` | Support bundle list _(derived)_ |
| `android_support_bundle_summarize` | Support bundle summarize _(derived)_ |
| `android_support_issue_draft` | Support issue draft _(derived)_ |
| `android_support_share_wizard` | Support share wizard _(derived)_ |

## android_tutorial_nudges

Tutorial nudges that surface the next helpful step after first use.

_No agent tools (passive/startup plugin)._

## android_ui_action_kit

Register Android UI action kit tools.

| Tool | Description |
|------|-------------|
| `android_ui_action_doctor` | Ui action doctor _(derived)_ |
| `android_ui_tap_match` | Ui tap match _(derived)_ |
| `android_ui_text_into_match` | Ui text into match _(derived)_ |

## android_ui_capability_audit_kit

Register UI capability audit tools.

| Tool | Description |
|------|-------------|
| `android_ui_capability_audit_doctor` | Ui capability audit doctor _(derived)_ |
| `android_ui_capability_audit_app` | Ui capability audit app _(derived)_ |
| `android_ui_capability_audit_stack` | Ui capability audit stack _(derived)_ |
| `android_ui_capability_audit_examples` | Ui capability audit examples _(derived)_ |

## android_ui_dump_kit

Register Android UI dump kit tools.

| Tool | Description |
|------|-------------|
| `android_ui_dump_doctor` | Ui dump doctor _(derived)_ |
| `android_ui_dump_hierarchy` | Ui dump hierarchy _(derived)_ |
| `android_ui_dump_find` | Ui dump find _(derived)_ |

## android_utility_kit

Register Android utility kit tools.

| Tool | Description |
|------|-------------|
| `android_utility_doctor` | Inspect Droid-native utility capability from Termux. |
| `android_open_settings` | Open a common Android settings screen by plain name. |
| `android_launch_app` | Launch an Android app by package name. |
| `android_share_text` | Open Android's share flow with plain text. |
| `android_find_apps` | Search installed package names by substring. |

## android_workflow_feasibility_kit

Register workflow feasibility assessment tools.

| Tool | Description |
|------|-------------|
| `android_workflow_feasibility_doctor` | Workflow feasibility doctor _(derived)_ |
| `android_workflow_feasibility_assess` | Workflow feasibility assess _(derived)_ |
| `android_workflow_feasibility_examples` | Workflow feasibility examples _(derived)_ |

## android_workflow_macro_kit

Register Android workflow macro tools.

| Tool | Description |
|------|-------------|
| `android_workflow_doctor` | Workflow doctor _(derived)_ |
| `android_workflow_list` | Workflow list _(derived)_ |
| `android_workflow_run` | Workflow run _(derived)_ |

## droidpuppy_doctor

Register the DroidPuppy master doctor tool.

| Tool | Description |
|------|-------------|
| `droidpuppy_doctor` | Run a full DroidPuppy stack health check (platform, commands, browsers, plugins). |

