#!/usr/bin/env python3
"""One-shot scheduler target for the eyes inbox lane."""

from __future__ import annotations

import argparse
import json

import eyes_inbox
import eyes_queue_worker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one eyes inbox scan + worker tick"
    )
    parser.add_argument(
        "--root",
        help="Override the eyes root directory (default: ~/.project_os/eyes).",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=1,
        help="Maximum queue items to process during this tick.",
    )
    parser.add_argument(
        "--skip-scan",
        action="store_true",
        help="Do not run inbox scan before consuming queue items.",
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Create review artifacts without posting local notifications.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    scan_summary = None
    if not args.skip_scan:
        scan_summary = eyes_inbox.scan_inbox(args.root)
    worker_summary = eyes_queue_worker.run_batch(
        args.root,
        max_items=args.max_items,
        notify_reviews=not args.no_notify,
    )
    print(
        json.dumps(
            {
                "scan": (
                    None
                    if scan_summary is None
                    else {
                        "scanned": scan_summary.scanned,
                        "ingested": scan_summary.ingested,
                        "duplicates": scan_summary.duplicates,
                        "failed": scan_summary.failed,
                        "pending_queue_items": scan_summary.pending_queue_items,
                    }
                ),
                "worker": {
                    "run_id": worker_summary.run_id,
                    "processed": worker_summary.processed,
                    "completed": worker_summary.completed,
                    "failed": worker_summary.failed,
                    "idle": worker_summary.idle,
                    "result_refs": worker_summary.result_refs,
                    "review_refs": worker_summary.review_refs,
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
