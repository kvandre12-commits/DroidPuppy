# Eyes Inbox

## Why this exists

The foreground phone surface is not where Project OS should get trapped.

If the operator can reach something with human navigation — a weird site, an
anti-bot flow, a login-gated page, a scroll-heavy app surface — then the system
needs a clean way to convert that human access into local machine work.

The **eyes inbox** is that handoff.

```text
human sees it
-> snapshots / exports / notes it
-> drops it into a bounded local inbox
-> intake worker validates and routes it
-> downstream workers process it without refighting security
```

## Doctrine fit

This lines up with the long-term Project OS trail:

- **Project OS**: the phone is a first-class operator surface, not a crippled desktop.
- **Orchestra**: the coordinator should delegate bounded work instead of being glued to the foreground.
- **Authority model**: the scheduler is not sovereign; it only routes bounded artifacts.
- **Runtime model**: the Project Run survives while individual workers come and go.
- **Android reality**: use human-native access and local storage instead of pretending every hostile surface can be automated directly.

## First implementation slice

Today's unlock is intentionally narrow:

- create a stable local folder layout
- accept manually dropped files
- generate validated artifact manifests
- emit routed queue items for downstream workers

No fake watcher daemon. No fake OCR engine. No pretending the hard parts are done.
Just a clean intake lane.

## Folder layout

Default root:

```text
~/.project_os/eyes/
```

Subdirectories:

```text
inbox/            raw human-dropped files
manifests/        validated EyesArtifact JSON
queue/pending/    queue items waiting for a worker
queue/claimed/    queue items temporarily claimed by a worker
queue/completed/  queue items that produced a result
queue/failed/     queue items that failed during worker execution
results/          validated EyesWorkerResult JSON
journal/events/   append-only worker execution/recovery event artifacts
journal/runs/     durable worker checkpoints (active/completed/failed/recovered)
review/pending/   review-required artifacts waiting for a human
review/approved/  review artifacts that were explicitly approved
review/rejected/  review artifacts that were explicitly rejected
review/review_required.json  latest review artifact, pending or decided
leases/active/    short-lived execution leases minted only on approval
audit/events/     immutable-ish decision trail with SHA-256 chain pointers
processed/        files successfully ingested
failed/           duplicate markers or error records
jobs/             generated Termux scheduler wrapper scripts
```

## Contracts

Supplemental v1 contracts:

- `contracts/v1/eyes_artifact.schema.json`
- `contracts/v1/eyes_queue_item.schema.json`
- `contracts/v1/eyes_worker_checkpoint.schema.json`
- `contracts/v1/eyes_worker_run_event.schema.json`

These are not replacements for the core five Orchestra contracts. They are a
bounded local intake seam that can later feed larger workflows.

## Tools and script

Repo-local worker commands:

```bash
python scripts/eyes_inbox.py init
python scripts/eyes_inbox.py status
python scripts/eyes_inbox.py scan
```

Optional custom root:

```bash
python scripts/eyes_inbox.py --root /path/to/eyes init
```

Low-friction Android ingress plugin:

- `android_eyes_inbox_doctor`
- `android_eyes_inbox_init`
- `android_eyes_inbox_status`
- `android_eyes_inbox_drop_text`
- `android_eyes_inbox_drop_url`
- `android_eyes_inbox_stage_file`
- `android_eyes_inbox_scan`

Headless worker + scheduler plugin:

- `android_eyes_worker_doctor`
- `android_eyes_worker_status`
- `android_eyes_worker_run_once`
- `android_eyes_worker_recover`
- `android_eyes_worker_schedule`
- `android_eyes_worker_list_jobs`
- `android_eyes_worker_cancel_job`

Repo-local worker scripts:

```bash
python scripts/eyes_queue_worker.py status
python scripts/eyes_queue_worker.py run-once --max-items 1
python scripts/eyes_queue_worker.py recover --stale-after-seconds 900
python scripts/eyes_tick.py --max-items 1
python scripts/eyes_review_gate.py --list-pending
python scripts/eyes_review_gate.py --approve <review_id> --decided-by butcher
python scripts/eyes_review_gate.py --reject <review_id> --decided-by butcher --reason "not safe"
```

The split is intentional:

- the **ingress plugin** is the cheap mail slot into the inbox
- the **queue worker** is the one-shot dancer that consumes pending work and exits
- the **scheduler wrapper** installs event-driven wakeups instead of fake forever loops

That keeps the operator path lightweight and lets background work happen when the system is ready for it.

## Routing behavior in the thin slice

Current routing is deliberately simple:

- image -> `ocr_review`
- html -> `page_summary`
- pdf -> `document_digest`
- json -> `structured_review`
- text -> `text_summary`
- bill-like keywords -> `bill_review`
- school-like keywords -> `school_digest`
- compare-like keywords -> `compare_candidate`
- anything weird -> `manual_triage`

This is enough to organize the pool before we teach more workers how to swim.

The current worker slice stays deterministic and bounded: it produces typed
result artifacts, updates queue status, emits a minimal `review_required` gate
artifact when human review is needed, and exits instead of clinging to life in a
background loop until Android strangles it.

It now also writes a durable per-run checkpoint plus append-only execution
journal events so a later `recover` pass can reconcile stale claimed queue items
instead of shrugging at a dead terminal.

## Why this matters

This is how we stop bonking the orchestrator's head on Android security walls.

The operator can use human-native access to surface evidence once, and the pack
can then work locally from the inbox forward.

That is the native advantage.

## Minimum governance loop now present

For review-requiring artifacts, the smallest closed loop is now:

```text
termux-job-scheduler
-> eyes_tick.py
-> eyes_queue_worker.py
-> review/pending/<id>.json
-> review/review_required.json
-> termux-notification
-> operator reviews
-> eyes_review_gate.py --approve/--reject
-> audit/events/<timestamp>_<id>.json
-> leases/active/<lease>.json on approval only
```

No dashboard. No daemon. No fake approval empire. Just enough to prove the
human gate belongs between recommendation and action.

Important honesty clause: the audit trail is currently **tamper-evident**, not a
full cryptographic signing system. Each decision event stores the original
review artifact snapshot, its SHA-256 digest, and the previous event hash so the
chain is obvious if somebody gets sneaky.
