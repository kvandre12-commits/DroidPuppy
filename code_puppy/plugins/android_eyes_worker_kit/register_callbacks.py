"""Register Android eyes worker tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_eyes_worker_cancel_job as android_eyes_worker_cancel_job_impl,
    android_eyes_worker_doctor as android_eyes_worker_doctor_impl,
    android_eyes_worker_examples as android_eyes_worker_examples_impl,
    android_eyes_worker_list_jobs as android_eyes_worker_list_jobs_impl,
    android_eyes_worker_recover as android_eyes_worker_recover_impl,
    android_eyes_worker_run_once as android_eyes_worker_run_once_impl,
    android_eyes_worker_schedule as android_eyes_worker_schedule_impl,
    android_eyes_worker_status as android_eyes_worker_status_impl,
)

_DOCTOR = "android_eyes_worker_doctor"
_STATUS = "android_eyes_worker_status"
_RUN_ONCE = "android_eyes_worker_run_once"
_RECOVER = "android_eyes_worker_recover"
_SCHEDULE = "android_eyes_worker_schedule"
_LIST_JOBS = "android_eyes_worker_list_jobs"
_CANCEL_JOB = "android_eyes_worker_cancel_job"
_EXAMPLES = "android_eyes_worker_examples"


def register_android_eyes_worker_doctor(agent: Any) -> None:
    @agent.tool
    async def android_eyes_worker_doctor(
        context: RunContext,
        root: str = "",
    ) -> dict[str, Any]:
        """Inspect eyes worker readiness, scripts, and scheduler capability."""
        del context
        return android_eyes_worker_doctor_impl(root=root)


def register_android_eyes_worker_status(agent: Any) -> None:
    @agent.tool
    async def android_eyes_worker_status(
        context: RunContext,
        root: str = "",
    ) -> dict[str, Any]:
        """Run the local queue worker status command and return its JSON output."""
        del context
        return android_eyes_worker_status_impl(root=root)


def register_android_eyes_worker_run_once(agent: Any) -> None:
    @agent.tool
    async def android_eyes_worker_run_once(
        context: RunContext,
        root: str = "",
        max_items: int = 1,
        scan_first: bool = True,
        notify_reviews: bool = True,
    ) -> dict[str, Any]:
        """Run one short-lived worker pass, optionally scanning inbox first."""
        del context
        return android_eyes_worker_run_once_impl(
            root=root,
            max_items=max_items,
            scan_first=scan_first,
            notify_reviews=notify_reviews,
        )


def register_android_eyes_worker_recover(agent: Any) -> None:
    @agent.tool
    async def android_eyes_worker_recover(
        context: RunContext,
        root: str = "",
        stale_after_seconds: int = 900,
        notify_reviews: bool = False,
    ) -> dict[str, Any]:
        """Reconcile stale claimed queue items after a crash or Android kill."""
        del context
        return android_eyes_worker_recover_impl(
            root=root,
            stale_after_seconds=stale_after_seconds,
            notify_reviews=notify_reviews,
        )


def register_android_eyes_worker_schedule(agent: Any) -> None:
    @agent.tool
    async def android_eyes_worker_schedule(
        context: RunContext,
        root: str = "",
        job_id: int = 4101,
        period_ms: int = 900000,
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
        del context
        return android_eyes_worker_schedule_impl(
            root=root,
            job_id=job_id,
            period_ms=period_ms,
            max_items=max_items,
            scan_first=scan_first,
            notify_reviews=notify_reviews,
            network=network,
            battery_not_low=battery_not_low,
            storage_not_low=storage_not_low,
            charging=charging,
            persisted=persisted,
            dry_run=dry_run,
        )


def register_android_eyes_worker_list_jobs(agent: Any) -> None:
    @agent.tool
    async def android_eyes_worker_list_jobs(context: RunContext) -> dict[str, Any]:
        """List pending Termux scheduler jobs."""
        del context
        return android_eyes_worker_list_jobs_impl()


def register_android_eyes_worker_cancel_job(agent: Any) -> None:
    @agent.tool
    async def android_eyes_worker_cancel_job(
        context: RunContext,
        job_id: int,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Cancel one scheduled eyes worker job by Termux job id."""
        del context
        return android_eyes_worker_cancel_job_impl(job_id=job_id, dry_run=dry_run)


def register_android_eyes_worker_examples(agent: Any) -> None:
    @agent.tool
    async def android_eyes_worker_examples(context: RunContext) -> dict[str, Any]:
        """Show example calls for the eyes worker and scheduler helpers."""
        del context
        return android_eyes_worker_examples_impl()


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_eyes_worker_doctor},
        {"name": _STATUS, "register_func": register_android_eyes_worker_status},
        {"name": _RUN_ONCE, "register_func": register_android_eyes_worker_run_once},
        {"name": _RECOVER, "register_func": register_android_eyes_worker_recover},
        {"name": _SCHEDULE, "register_func": register_android_eyes_worker_schedule},
        {"name": _LIST_JOBS, "register_func": register_android_eyes_worker_list_jobs},
        {"name": _CANCEL_JOB, "register_func": register_android_eyes_worker_cancel_job},
        {"name": _EXAMPLES, "register_func": register_android_eyes_worker_examples},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [
        _DOCTOR,
        _STATUS,
        _RUN_ONCE,
        _RECOVER,
        _SCHEDULE,
        _LIST_JOBS,
        _CANCEL_JOB,
        _EXAMPLES,
    ]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
