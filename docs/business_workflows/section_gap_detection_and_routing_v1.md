# section_gap_detection_and_routing_v1

## Summary

This workflow models a retail-floor visibility loop:

A moving capture source such as a Zamboni, floor robot, or routine sweep process:
- captures images of store sections
- detects likely empty or severely depleted sections
- turns detections into operational alerts
- routes each alert to the right owner
- builds a history that can expose recurring workflow failures

This is a strong automation candidate because it combines:
- evidence capture
- image review or computer vision
- ownership routing
- escalation
- trend analysis
- workflow improvement feedback

## Industry fit

Primary fit:
- retail
- grocery
- big-box operations
- store-floor replenishment

Also applicable to:
- warehouse slot audits
- cooler/freezer audits
- merchandising compliance
- field photo inspection workflows

## Business goal

Detect empty shelf or section conditions early enough to trigger action, route them to the right people, and learn which recurring failures suggest process changes.

## Human reality

Leadership usually wants answers to a few brutal little questions:
- What section is empty?
- How bad is it?
- When did it happen?
- Is this a stocking problem, inventory mismatch, merchandising issue, or execution miss?
- Who owns the fix right now?
- Is this happening over and over in the same place?

## Typical current manual flow

1. A machine or worker captures photos during routine movement
2. Someone reviews the photos later or notices the issue in passing
3. The issue is described manually in chat, email, or a call
4. Another person figures out who owns that section
5. Someone follows up to confirm whether it was fixed
6. Later, leadership tries to reconstruct the pattern from memory

## Common pain points

- empty sections are discovered too late
- photo evidence exists but is not converted into fast action
- the right owner is not obvious at alert time
- repeated issues in the same area are hard to quantify
- workers waste time translating images into messages
- root causes get mixed together with one-off misses
- leaders can see symptoms without seeing process failure patterns

## Desired success criteria

- flag likely empty sections shortly after capture
- attach image, section, and timestamp context automatically
- route alerts to the right role or person with minimal manual work
- track acknowledgement and fix status
- build a simple recurring-gap history by area and time window
- surface workflow patterns that suggest staffing, replenishment, or planogram changes
- keep false positives low enough that teams trust the system

## Workflow pipeline

### Stage 1 — capture
Possible sources:
- Zamboni-mounted camera
- floor scrubber or robot camera
- employee phone photo sweep
- fixed camera snapshots

### Stage 2 — detect
Convert images into a simple operational event:
- `section_gap_detected`

Detection can begin with very humble logic:
- low visual fill threshold
- known-empty facing count
- before/after comparison against a normal shelf image
- human review confirmation on borderline cases

Do not overcomplicate v1 with magical AI nonsense.
A boring, explainable detector beats a fancy liar.

### Stage 3 — classify
Each detection should carry:
- store
- aisle or section
- timestamp
- confidence score
- severity
- image reference
- suspected issue type

Suspected issue types may include:
- replenishment delay
- inventory mismatch
- planogram/compliance issue
- stocking execution miss
- unknown_needs_review

### Stage 4 — route
Map the detection to the likely owner:
- section owner
- department lead
- stock team
- inventory control
- merchandising
- regional escalation

This is the part that answers your “who do we ask to fix it?” question.

The routing table is a first-class artifact, not tribal memory.

### Stage 5 — notify
Send a compact alert with:
- what was detected
- where
- how severe
- image link
- who owns next action
- optional due-by expectation

### Stage 6 — learn
Aggregate recurring detections by:
- section
- time of day
- day of week
- crew or shift
- store
- issue type

That creates the workflow-improvement layer instead of just a fancy tattletale machine.

## Example app stack

Early DroidPuppy-friendly support stack example:
- `com.sec.android.app.camera`
- `com.google.android.apps.photos`
- `com.brave.browser`
- `com.microsoft.teams`
- `com.microsoft.office.outlook`

This is not claiming the Zamboni itself runs these apps.
It means the mobile support, review, and escalation path can start here.

## DroidPuppy intervention points

### Intervention 1 — capture and review handoff
DroidPuppy can help move evidence into a review surface or dashboard.

Relevant tools:
- `android_handoff_url`
- `android_handoff_text`
- `android_intent_send`

### Intervention 2 — operator alert packaging
Once a likely section gap exists, DroidPuppy can package a readable alert for Teams or Outlook.

Relevant tools:
- `android_handoff_text`
- `android_support_share_wizard`
- `android_intent_send`

### Intervention 3 — UI fallback
If evidence must be reviewed inside camera or photo apps, DroidPuppy can use launch + UI steering as a fallback.

Relevant tools:
- `android_ui_dump_hierarchy`
- `android_ui_dump_find`
- `android_ui_tap_match`
- `android_input_text`

### Intervention 4 — support and audit trail
When workflows break or routing is unclear, DroidPuppy can preserve context and artifacts.

Relevant tools:
- `android_support_bundle_collect`
- `android_support_issue_draft`
- `android_support_share_wizard`

## Execution model

### Best-case lane
- image captured
- detector flags likely gap
- routing table identifies owner
- alert sent with image and context
- fix confirmed
- event logged for trend review

### Fallback lane
- image captured
- detector confidence is low
- human review confirms or rejects
- approved alert is routed

### Learning lane
- repeated gap events cluster around the same sections or times
- leadership uses that history to redesign workflow

## Recommended pilot

Pilot one store, one aisle family, and one alert destination first.

Good v1 shape:
1. collect images from one repeatable route
2. detect only obvious severe gaps
3. route alerts to one channel such as Teams
4. track whether alerts were correct and actionable
5. review repeat offenders weekly for process changes

## V1 rollout phases

### Phase 1 — routing map and data model
Define:
- section identifiers
- owner mapping
- alert schema
- severity rules
- review queue

### Phase 2 — evidence-to-alert pilot
Build the cheapest useful win:
- image in
- gap flag out
- owner attached
- alert sent

### Phase 3 — confirmation loop
Add:
- acknowledged/unacknowledged state
- fixed/not fixed state
- false positive tracking

### Phase 4 — workflow analytics
Add reporting on:
- repeat section failures
- timing patterns
- likely root-cause clusters
- recommended workflow experiments

## Risks

- false positives will destroy trust fast
- missing or weak section identifiers will break routing
- ownership maps may be outdated or political
- camera angle and lighting may reduce detection quality
- a perfect alert without a fix process is still useless
- if nobody closes the loop, you get a dashboard instead of improvement

## Support posture

Never promise “AI solved it” without:
- human review for borderline cases
- a clear owner map
- a visible fix-status loop
- a recurring-pattern review process

## Definition of done for v1

This workflow reaches v1 usefulness when the system can:
- detect obvious empty-section events
- package image + section + time into an alert
- identify the likely owner automatically
- send the alert into the real operating channel
- produce a weekly pattern view that leadership can use

## Next likely versions

- `section_gap_detection_and_routing_v2`
  - introduces store-specific routing maps
- `section_gap_detection_and_routing_v3`
  - adds confidence tuning and human-review queue
- `section_gap_detection_and_routing_v4`
  - adds recurring-root-cause analytics and workflow experiment tracking
