# order_picking_and_confirmation_v1

## Summary

This workflow models a common operations problem:

A worker needs to:
- review the next order or pick task
- locate the right item
- confirm the correct quantity or state
- mark progress in the right app
- escalate when the item, quantity, or location does not match expectations

This is a strong DroidPuppy workflow because it naturally combines:
- repetitive task flow
- app switching
- state confirmation
- mismatch escalation
- support evidence and carryover

## Industry fit

Primary fit:
- retail
- warehouse operations
- fulfillment
- inventory handling

Also applicable to:
- grocery picking
- delivery staging
- field-parts confirmation
- backroom operations

## Business goal

Reduce friction and mismatch risk during order picking and confirmation.

## Human reality

The operator is usually trying to answer:
- Is this the right item?
- Is this the right quantity?
- Is this location or bin correct?
- Has this step really been confirmed in the app?
- What do I do when the app and reality do not match?

## Typical current manual flow

1. Open the picking or task app
2. Review the next item or order line
3. Physically locate the item
4. Check quantity or variant
5. Confirm the result in the app
6. Switch to another app or message if something is wrong
7. Re-type the mismatch details manually
8. Rebuild context later if follow-up is needed

## Common pain points

- repeated confirmation steps across awkward app screens
- mismatch between physical reality and app state
- too much retyping when escalating a missing or wrong item
- unclear completion state
- workers lose time bouncing between picking and escalation tools
- issue evidence is often weak or delayed

## Desired success criteria

- faster confirmation flow
- fewer app-switching interruptions
- cleaner mismatch escalation
- less ambiguity about completion state
- more dependable evidence when something is wrong
- less repeated rework on the same pick problem

## Example app stack

This workflow is intentionally generic.
Possible app categories:
- picking or fulfillment app
- browser-based internal dashboard
- messaging or escalation channel
- support/evidence path

Early DroidPuppy-friendly stack example:
- `com.brave.browser`
- `com.termux`
- plus one real picking or fulfillment target when available

## DroidPuppy intervention points

### Intervention 1 — task entry and task state
DroidPuppy can help reach the task surface reliably and inspect how structured the app is.

Relevant tools:
- `android_app_profile`
- `android_workflow_feasibility_assess`
- `android_intent_audit_stack`

### Intervention 2 — confirmation support
DroidPuppy can reduce friction around repeated confirmation by helping move context and standardize follow-up actions.

Relevant tools:
- `android_handoff_text`
- `android_app_workflow_run`
- `android_intent_send`

### Intervention 3 — mismatch escalation
When the pick cannot be completed cleanly, DroidPuppy can:
- draft issue summaries
- preserve support evidence
- move the escalation outward faster

Relevant tools:
- `android_support_issue_draft`
- `android_support_bundle_collect`
- `android_support_share_wizard`

### Intervention 4 — UI fallback
If the picking app is closed or awkward, DroidPuppy can use UI steering.

Relevant tools:
- `android_ui_capability_audit_app`
- `android_ui_dump_hierarchy`
- `android_ui_dump_find`
- `android_ui_tap_match`
- `android_input_text`

## Execution model

### Best-case lane
- enter the task surface directly
- confirm the item state with minimal switching
- escalate only when needed with cleaner structured handoff

### Fallback lane
- launch app
- inspect visible task state
- navigate through confirmation screens
- gather issue details when the task fails
- share outward

### Support lane
- preserve mismatch context before it gets blurred by repeated retries

## Recommended pilot

Pilot a narrow picking routine around one repeated confirmation pain point.

Good early pilot shape:
1. reach the picking surface reliably
2. reduce one manual step around confirmation or follow-up
3. create a cleaner path for mismatch escalation
4. preserve support context when a pick fails

## V1 rollout phases

### Phase 1 — stack audit
Identify:
- which app owns the picking flow
- where mismatches are currently escalated
- whether direct handoff is available
- whether the picking path will require UI steering

Relevant tools:
- `android_app_inventory_list`
- `android_app_profile`
- `android_workflow_feasibility_assess`
- `android_intent_audit_stack`
- `android_ui_capability_audit_stack`

### Phase 2 — direct handoff pilot
Build the cheapest useful win:
- reduce manual retyping between task context and escalation destination

Relevant tools:
- `android_handoff_text`
- `android_intent_send`
- `android_app_workflow_run`

### Phase 3 — mismatch packaging
Make mismatch handling stronger:
- issue draft
- support summary
- evidence path

Relevant tools:
- `android_support_issue_draft`
- `android_support_bundle_collect`
- `android_support_share_wizard`

### Phase 4 — UI-guided expansion
For closed or awkward picking apps:
- inspect task state
- locate relevant controls
- step through confirmation screens with care

Relevant tools:
- `android_ui_capability_audit_stack`
- `android_ui_dump_hierarchy`
- `android_ui_dump_find`
- `android_ui_tap_match`

## Risks

- picking flow may be trapped in a closed app
- completion state may be hard to verify cleanly
- mismatch escalation may depend on informal team habits
- disconnected ADB limits screen-driven fallback work
- workers will abandon the flow if it adds even small delay under pressure

## Support posture

Never treat pick failures as simple exceptions.

DroidPuppy should preserve:
- item mismatch summary
- visible task state
- escalation-ready context
- support evidence when the system and reality disagree

## Definition of done for v1

This workflow reaches v1 usefulness when DroidPuppy can help a worker:
- reach the picking state faster
- reduce at least one confirmation or follow-up friction step
- produce a cleaner mismatch escalation path
- preserve context when a pick cannot be completed cleanly

## Next likely versions

- `order_picking_and_confirmation_v2`
  - introduces app-specific picking variants
- `order_picking_and_confirmation_retail_variant`
  - optimized for store-floor pick and stage routines
- `order_picking_and_confirmation_warehouse_variant`
  - optimized for bins, quantities, and fulfillment confirmation
