from __future__ import annotations

import datetime as dt
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_EYES_ROOT = Path.home() / ".project_os" / "eyes"


@dataclass(frozen=True)
class EyesPaths:
    root: Path
    inbox: Path
    manifests: Path
    queue_pending: Path
    processed: Path
    failed: Path


def _now_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _clean_name(name: str, *, fallback_prefix: str, fallback_suffix: str) -> str:
    raw = (name or "").strip().replace("/", "_")
    if not raw:
        return f"{fallback_prefix}_{_now_stamp()}{fallback_suffix}"
    path = Path(raw)
    stem = path.stem.strip().replace(" ", "_") or f"{fallback_prefix}_{_now_stamp()}"
    suffix = path.suffix or fallback_suffix
    return f"{stem}{suffix}"


def _unique_path(directory: Path, file_name: str) -> Path:
    candidate = directory / file_name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2
    while True:
        retry = directory / f"{stem}_{counter}{suffix}"
        if not retry.exists():
            return retry
        counter += 1


def resolve_paths(root: str = "") -> EyesPaths:
    base = Path(root).expanduser().resolve() if root.strip() else DEFAULT_EYES_ROOT
    return EyesPaths(
        root=base,
        inbox=base / "inbox",
        manifests=base / "manifests",
        queue_pending=base / "queue" / "pending",
        processed=base / "processed",
        failed=base / "failed",
    )


def ensure_layout(root: str = "") -> EyesPaths:
    paths = resolve_paths(root)
    for path in (
        paths.root,
        paths.inbox,
        paths.manifests,
        paths.queue_pending,
        paths.processed,
        paths.failed,
    ):
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _status_counts(paths: EyesPaths) -> dict[str, int | str]:
    return {
        "root": str(paths.root),
        "inbox_files": len([path for path in paths.inbox.iterdir() if path.is_file()]),
        "manifests": len(list(paths.manifests.glob("*.json"))),
        "pending_queue_items": len(list(paths.queue_pending.glob("*.json"))),
        "processed_files": len(
            [path for path in paths.processed.iterdir() if path.is_file()]
        ),
        "failed_records": len(list(paths.failed.glob("*.json"))),
    }


def _resolve_scanner_script() -> Path | None:
    env_override = Path.home() / ".project_os" / "eyes" / "scanner.py"
    candidates = [
        Path.cwd() / "scripts" / "eyes_inbox.py",
        Path(__file__).resolve().parents[4] / "scripts" / "eyes_inbox.py",
        env_override,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def _run_command(args: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": True,
            "args": args,
            "exit_code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "args": args,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "error": f"command not found: {exc}",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "args": args,
            "exit_code": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "error": f"command timed out after {timeout}s",
        }


def _maybe_scan(root: str, scan_now: bool) -> dict[str, Any] | None:
    if not scan_now:
        return None
    return android_eyes_inbox_scan(root=root)


def android_eyes_inbox_doctor(root: str = "") -> dict[str, Any]:
    """Inspect local eyes inbox readiness and optional scanner availability."""
    paths = resolve_paths(root)
    scanner_script = _resolve_scanner_script()
    return {
        "success": True,
        "paths": {
            "root": str(paths.root),
            "inbox": str(paths.inbox),
            "manifests": str(paths.manifests),
            "queue_pending": str(paths.queue_pending),
            "processed": str(paths.processed),
            "failed": str(paths.failed),
        },
        "exists": {
            "root": paths.root.exists(),
            "inbox": paths.inbox.exists(),
            "manifests": paths.manifests.exists(),
            "queue_pending": paths.queue_pending.exists(),
            "processed": paths.processed.exists(),
            "failed": paths.failed.exists(),
        },
        "capabilities": {
            "drop_text": True,
            "drop_url": True,
            "stage_file": True,
            "scan_now": bool(scanner_script),
        },
        "scanner_script": str(scanner_script) if scanner_script else None,
        "guidance": [
            "Use android_eyes_inbox_init once to create the local folder layout.",
            "Use android_eyes_inbox_drop_text or android_eyes_inbox_drop_url for low-friction manual captures.",
            "Use android_eyes_inbox_stage_file for screenshots, PDFs, or exports you already have on disk.",
            "If scan_now is unavailable, run the repo-local eyes inbox worker separately.",
        ],
    }


def android_eyes_inbox_init(root: str = "") -> dict[str, Any]:
    """Create the local eyes inbox folder layout."""
    paths = ensure_layout(root)
    return {
        "success": True,
        "root": str(paths.root),
        "created": {
            "inbox": str(paths.inbox),
            "manifests": str(paths.manifests),
            "queue_pending": str(paths.queue_pending),
            "processed": str(paths.processed),
            "failed": str(paths.failed),
        },
        "scanner_available": bool(_resolve_scanner_script()),
    }


def android_eyes_inbox_status(root: str = "") -> dict[str, Any]:
    """Report file counts for the local eyes inbox."""
    paths = ensure_layout(root)
    return {
        "success": True,
        "status": _status_counts(paths),
        "scanner_available": bool(_resolve_scanner_script()),
    }


def android_eyes_inbox_drop_text(
    text: str,
    root: str = "",
    name: str = "",
    scan_now: bool = False,
) -> dict[str, Any]:
    """Write plain text directly into the eyes inbox as a note."""
    if not text.strip():
        raise ValueError("text is required")
    paths = ensure_layout(root)
    file_name = _clean_name(name, fallback_prefix="note", fallback_suffix=".txt")
    destination = _unique_path(paths.inbox, file_name)
    destination.write_text(text)
    return {
        "success": True,
        "root": str(paths.root),
        "file_path": str(destination),
        "bytes_written": destination.stat().st_size,
        "scan_result": _maybe_scan(root, scan_now),
    }


def android_eyes_inbox_drop_url(
    url: str,
    root: str = "",
    name: str = "",
    note: str = "",
    scan_now: bool = False,
) -> dict[str, Any]:
    """Write a URL and optional note into the eyes inbox for later review."""
    if not url.strip():
        raise ValueError("url is required")
    paths = ensure_layout(root)
    file_name = _clean_name(name, fallback_prefix="url", fallback_suffix=".txt")
    destination = _unique_path(paths.inbox, file_name)
    body = url.strip()
    if note.strip():
        body += f"\n\n{note.strip()}"
    destination.write_text(body + "\n")
    return {
        "success": True,
        "root": str(paths.root),
        "file_path": str(destination),
        "bytes_written": destination.stat().st_size,
        "scan_result": _maybe_scan(root, scan_now),
    }


def android_eyes_inbox_stage_file(
    file_path: str,
    root: str = "",
    move: bool = False,
    name: str = "",
    scan_now: bool = False,
) -> dict[str, Any]:
    """Copy or move an existing local file into the eyes inbox."""
    source = Path(file_path).expanduser().resolve()
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    paths = ensure_layout(root)
    file_name = _clean_name(
        name, fallback_prefix=source.stem, fallback_suffix=source.suffix
    )
    destination = _unique_path(paths.inbox, file_name)
    if move:
        shutil.move(str(source), str(destination))
    else:
        shutil.copy2(source, destination)
    return {
        "success": True,
        "root": str(paths.root),
        "file_path": str(destination),
        "mode": "move" if move else "copy",
        "bytes_written": destination.stat().st_size,
        "scan_result": _maybe_scan(root, scan_now),
    }


def android_eyes_inbox_scan(root: str = "") -> dict[str, Any]:
    """Run the repo-local eyes inbox intake worker when available."""
    ensure_layout(root)
    script_path = _resolve_scanner_script()
    if script_path is None:
        return {
            "success": False,
            "message": "No repo-local eyes inbox scanner script was found.",
            "guidance": [
                "Run this from a DroidPuppy checkout that contains scripts/eyes_inbox.py.",
                "Or stage files now and process them later with the local worker.",
            ],
        }
    command = [sys.executable, str(script_path)]
    if root.strip():
        command.extend(["--root", str(Path(root).expanduser().resolve())])
    command.append("scan")
    result = _run_command(command, timeout=60)
    return {
        "success": result.get("exit_code") == 0,
        "scanner_script": str(script_path),
        "command": command,
        "result": result,
    }


def android_eyes_inbox_examples() -> dict[str, Any]:
    """Show example calls for the Android eyes inbox helpers."""
    return {
        "success": True,
        "examples": [
            {
                "name": "drop_plain_text",
                "example_args": {
                    "text": "This school deadline moved to Friday.",
                    "scan_now": False,
                },
            },
            {
                "name": "drop_url_with_note",
                "example_args": {
                    "url": "https://example.com",
                    "note": "This page matters; weird login flow, human reached it manually.",
                    "scan_now": False,
                },
            },
            {
                "name": "stage_screenshot_and_scan",
                "example_args": {
                    "file_path": "/sdcard/Pictures/Screenshots/example.png",
                    "scan_now": True,
                },
            },
        ],
    }
