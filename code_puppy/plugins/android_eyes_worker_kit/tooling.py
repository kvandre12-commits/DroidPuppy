from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_EYES_ROOT = Path.home() / ".project_os" / "eyes"
DEFAULT_JOB_ID = 4101
DEFAULT_PERIOD_MS = 900_000


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


def _resolve_script(name: str) -> Path | None:
    candidates = [
        Path.cwd() / "scripts" / name,
        Path(__file__).resolve().parents[4] / "scripts" / name,
        Path.home() / ".project_os" / "eyes" / name,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def _resolve_root(root: str = "") -> Path:
    return Path(root).expanduser().resolve() if root.strip() else DEFAULT_EYES_ROOT


def _jobs_dir(root: str = "") -> Path:
    directory = _resolve_root(root) / "jobs"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _scheduler_bin() -> str | None:
    return shutil.which("termux-job-scheduler")


def _tick_wrapper_path(root: str, job_id: int) -> Path:
    return _jobs_dir(root) / f"eyes_tick_job_{job_id}.sh"


def _create_wrapper_script(
    *,
    root: str,
    job_id: int,
    max_items: int,
    scan_first: bool,
    notify_reviews: bool,
) -> dict[str, Any]:
    tick_script = _resolve_script("eyes_tick.py")
    if tick_script is None:
        raise FileNotFoundError("eyes_tick.py was not found")
    repo_root = tick_script.parent.parent
    bash_path = shutil.which("bash") or "/system/bin/sh"
    args = [
        sys.executable,
        str(tick_script),
        "--root",
        str(_resolve_root(root)),
        "--max-items",
        str(max_items),
    ]
    if not scan_first:
        args.append("--skip-scan")
    if not notify_reviews:
        args.append("--no-notify")
    wrapper_path = _tick_wrapper_path(root, job_id)
    command = " ".join(shlex.quote(part) for part in args)
    content = (
        f"#!{bash_path}\ncd {shlex.quote(str(repo_root))} || exit 1\nexec {command}\n"
    )
    wrapper_path.write_text(content)
    wrapper_path.chmod(0o755)
    return {
        "wrapper_path": str(wrapper_path),
        "tick_script": str(tick_script),
        "repo_root": str(repo_root),
        "command": args,
    }


def android_eyes_worker_doctor(root: str = "") -> dict[str, Any]:
    """Inspect eyes worker readiness, scripts, and scheduler capability."""
    resolved_root = _resolve_root(root)
    queue_worker = _resolve_script("eyes_queue_worker.py")
    tick_script = _resolve_script("eyes_tick.py")
    scheduler = _scheduler_bin()
    return {
        "success": True,
        "root": str(resolved_root),
        "scripts": {
            "eyes_queue_worker": str(queue_worker) if queue_worker else None,
            "eyes_tick": str(tick_script) if tick_script else None,
        },
        "commands": {
            "termux-job-scheduler": scheduler,
            "python": sys.executable,
            "termux-notification": shutil.which("termux-notification"),
        },
        "capabilities": {
            "run_once": bool(queue_worker),
            "recover": bool(queue_worker),
            "scheduled_tick": bool(queue_worker and tick_script and scheduler),
            "review_notifications": bool(shutil.which("termux-notification")),
            "list_jobs": bool(scheduler),
            "cancel_job": bool(scheduler),
        },
        "guidance": [
            "Use android_eyes_worker_run_once for an immediate bounded pass.",
            "Use android_eyes_worker_recover if Android killed a worker mid-claim.",
            "Use android_eyes_worker_schedule to install a Termux scheduler tick.",
            "Keep workers one-shot and short-lived; Android punishes fake daemons.",
        ],
    }


def android_eyes_worker_status(root: str = "") -> dict[str, Any]:
    """Run the local queue worker status command and return its JSON output."""
    worker_script = _resolve_script("eyes_queue_worker.py")
    if worker_script is None:
        return {"success": False, "message": "eyes_queue_worker.py was not found."}
    command = [sys.executable, str(worker_script)]
    if root.strip():
        command.extend(["--root", str(_resolve_root(root))])
    command.append("status")
    result = _run_command(command, timeout=30)
    parsed = None
    if result.get("exit_code") == 0 and result.get("stdout"):
        try:
            parsed = json.loads(str(result["stdout"]))
        except json.JSONDecodeError:
            parsed = None
    return {
        "success": result.get("exit_code") == 0,
        "command": command,
        "result": result,
        "status": parsed,
    }


def android_eyes_worker_run_once(
    root: str = "",
    max_items: int = 1,
    scan_first: bool = True,
    notify_reviews: bool = True,
) -> dict[str, Any]:
    """Run one short-lived worker pass, optionally scanning inbox first."""
    script_name = "eyes_tick.py" if scan_first else "eyes_queue_worker.py"
    script_path = _resolve_script(script_name)
    if script_path is None:
        return {
            "success": False,
            "message": f"{script_name} was not found.",
        }
    command = [sys.executable, str(script_path)]
    if root.strip():
        command.extend(["--root", str(_resolve_root(root))])
    if scan_first:
        command.extend(["--max-items", str(max_items)])
        if not notify_reviews:
            command.append("--no-notify")
    else:
        command.extend(["run-batch", "--max-items", str(max_items)])
        if not notify_reviews:
            command.append("--no-notify")
    result = _run_command(command, timeout=60)
    parsed = None
    if result.get("exit_code") == 0 and result.get("stdout"):
        try:
            parsed = json.loads(str(result["stdout"]))
        except json.JSONDecodeError:
            parsed = None
    return {
        "success": result.get("exit_code") == 0,
        "command": command,
        "result": result,
        "summary": parsed,
    }


def android_eyes_worker_recover(
    root: str = "",
    stale_after_seconds: int = 900,
    notify_reviews: bool = False,
) -> dict[str, Any]:
    """Reconcile stale claimed queue items after a crash or Android kill."""
    worker_script = _resolve_script("eyes_queue_worker.py")
    if worker_script is None:
        return {"success": False, "message": "eyes_queue_worker.py was not found."}
    command = [sys.executable, str(worker_script)]
    if root.strip():
        command.extend(["--root", str(_resolve_root(root))])
    command.extend(["recover", "--stale-after-seconds", str(stale_after_seconds)])
    if not notify_reviews:
        command.append("--no-notify")
    result = _run_command(command, timeout=60)
    parsed = None
    if result.get("exit_code") == 0 and result.get("stdout"):
        try:
            parsed = json.loads(str(result["stdout"]))
        except json.JSONDecodeError:
            parsed = None
    return {
        "success": result.get("exit_code") == 0,
        "command": command,
        "result": result,
        "recovery": parsed,
    }


def android_eyes_worker_schedule(
    root: str = "",
    job_id: int = DEFAULT_JOB_ID,
    period_ms: int = DEFAULT_PERIOD_MS,
    max_items: int = 1,
    scan_first: bool = True,
    notify_reviews: bool = True,
    network: str = "any",
    battery_not_low: bool = True,
    storage_not_low: bool = False,
    charging: bool = False,
    persisted: bool = False,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Create a Termux scheduler wrapper for the eyes worker tick."""
    scheduler = _scheduler_bin()
    if scheduler is None:
        return {
            "success": False,
            "message": "termux-job-scheduler is not available.",
        }
    wrapper = _create_wrapper_script(
        root=root,
        job_id=job_id,
        max_items=max_items,
        scan_first=scan_first,
        notify_reviews=notify_reviews,
    )
    command = [
        scheduler,
        "--script",
        str(wrapper["wrapper_path"]),
        "--job-id",
        str(job_id),
        "--period-ms",
        str(period_ms),
        "--network",
        network,
        "--battery-not-low",
        str(battery_not_low).lower(),
        "--storage-not-low",
        str(storage_not_low).lower(),
        "--charging",
        str(charging).lower(),
        "--persisted",
        str(persisted).lower(),
    ]
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "wrapper": wrapper,
            "command": command,
        }
    result = _run_command(command, timeout=45)
    return {
        "success": result.get("exit_code") == 0,
        "dry_run": False,
        "wrapper": wrapper,
        "command": command,
        "result": result,
    }


def android_eyes_worker_list_jobs() -> dict[str, Any]:
    """List pending Termux scheduler jobs."""
    scheduler = _scheduler_bin()
    if scheduler is None:
        return {
            "success": False,
            "message": "termux-job-scheduler is not available.",
        }
    command = [scheduler, "--pending"]
    result = _run_command(command, timeout=30)
    return {
        "success": result.get("exit_code") == 0,
        "command": command,
        "result": result,
    }


def android_eyes_worker_cancel_job(job_id: int, dry_run: bool = True) -> dict[str, Any]:
    """Cancel one scheduled eyes worker job by Termux job id."""
    scheduler = _scheduler_bin()
    if scheduler is None:
        return {
            "success": False,
            "message": "termux-job-scheduler is not available.",
        }
    command = [scheduler, "--cancel", "--job-id", str(job_id)]
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "command": command,
        }
    result = _run_command(command, timeout=30)
    return {
        "success": result.get("exit_code") == 0,
        "dry_run": False,
        "command": command,
        "result": result,
    }


def android_eyes_worker_examples() -> dict[str, Any]:
    """Show example calls for the eyes worker and scheduler helpers."""
    return {
        "success": True,
        "examples": [
            {
                "name": "run_one_tick_now",
                "example_args": {
                    "scan_first": True,
                    "max_items": 1,
                },
            },
            {
                "name": "recover_stale_claims",
                "example_args": {
                    "stale_after_seconds": 900,
                    "notify_reviews": False,
                },
            },
            {
                "name": "schedule_every_15_minutes",
                "example_args": {
                    "job_id": 4101,
                    "period_ms": 900000,
                    "max_items": 1,
                    "dry_run": True,
                },
            },
            {
                "name": "cancel_a_job",
                "example_args": {
                    "job_id": 4101,
                    "dry_run": True,
                },
            },
        ],
    }
