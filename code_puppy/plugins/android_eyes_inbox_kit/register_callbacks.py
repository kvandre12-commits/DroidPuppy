"""Register Android eyes inbox tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_eyes_inbox_doctor as android_eyes_inbox_doctor_impl,
    android_eyes_inbox_drop_text as android_eyes_inbox_drop_text_impl,
    android_eyes_inbox_drop_url as android_eyes_inbox_drop_url_impl,
    android_eyes_inbox_examples as android_eyes_inbox_examples_impl,
    android_eyes_inbox_init as android_eyes_inbox_init_impl,
    android_eyes_inbox_scan as android_eyes_inbox_scan_impl,
    android_eyes_inbox_stage_file as android_eyes_inbox_stage_file_impl,
    android_eyes_inbox_status as android_eyes_inbox_status_impl,
)

_DOCTOR = "android_eyes_inbox_doctor"
_INIT = "android_eyes_inbox_init"
_STATUS = "android_eyes_inbox_status"
_DROP_TEXT = "android_eyes_inbox_drop_text"
_DROP_URL = "android_eyes_inbox_drop_url"
_STAGE_FILE = "android_eyes_inbox_stage_file"
_SCAN = "android_eyes_inbox_scan"
_EXAMPLES = "android_eyes_inbox_examples"


def register_android_eyes_inbox_doctor(agent: Any) -> None:
    @agent.tool
    async def android_eyes_inbox_doctor(
        context: RunContext,
        root: str = "",
    ) -> dict[str, Any]:
        """Inspect local eyes inbox readiness and optional scanner availability."""
        del context
        return android_eyes_inbox_doctor_impl(root=root)


def register_android_eyes_inbox_init(agent: Any) -> None:
    @agent.tool
    async def android_eyes_inbox_init(
        context: RunContext,
        root: str = "",
    ) -> dict[str, Any]:
        """Create the local eyes inbox folder layout."""
        del context
        return android_eyes_inbox_init_impl(root=root)


def register_android_eyes_inbox_status(agent: Any) -> None:
    @agent.tool
    async def android_eyes_inbox_status(
        context: RunContext,
        root: str = "",
    ) -> dict[str, Any]:
        """Report file counts for the local eyes inbox."""
        del context
        return android_eyes_inbox_status_impl(root=root)


def register_android_eyes_inbox_drop_text(agent: Any) -> None:
    @agent.tool
    async def android_eyes_inbox_drop_text(
        context: RunContext,
        text: str,
        root: str = "",
        name: str = "",
        scan_now: bool = False,
    ) -> dict[str, Any]:
        """Write plain text directly into the eyes inbox as a note."""
        del context
        return android_eyes_inbox_drop_text_impl(
            text=text,
            root=root,
            name=name,
            scan_now=scan_now,
        )


def register_android_eyes_inbox_drop_url(agent: Any) -> None:
    @agent.tool
    async def android_eyes_inbox_drop_url(
        context: RunContext,
        url: str,
        root: str = "",
        name: str = "",
        note: str = "",
        scan_now: bool = False,
    ) -> dict[str, Any]:
        """Write a URL and optional note into the eyes inbox for later review."""
        del context
        return android_eyes_inbox_drop_url_impl(
            url=url,
            root=root,
            name=name,
            note=note,
            scan_now=scan_now,
        )


def register_android_eyes_inbox_stage_file(agent: Any) -> None:
    @agent.tool
    async def android_eyes_inbox_stage_file(
        context: RunContext,
        file_path: str,
        root: str = "",
        move: bool = False,
        name: str = "",
        scan_now: bool = False,
    ) -> dict[str, Any]:
        """Copy or move an existing local file into the eyes inbox."""
        del context
        return android_eyes_inbox_stage_file_impl(
            file_path=file_path,
            root=root,
            move=move,
            name=name,
            scan_now=scan_now,
        )


def register_android_eyes_inbox_scan(agent: Any) -> None:
    @agent.tool
    async def android_eyes_inbox_scan(
        context: RunContext,
        root: str = "",
    ) -> dict[str, Any]:
        """Run the repo-local eyes inbox intake worker when available."""
        del context
        return android_eyes_inbox_scan_impl(root=root)


def register_android_eyes_inbox_examples(agent: Any) -> None:
    @agent.tool
    async def android_eyes_inbox_examples(context: RunContext) -> dict[str, Any]:
        """Show example calls for the Android eyes inbox helpers."""
        del context
        return android_eyes_inbox_examples_impl()


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_eyes_inbox_doctor},
        {"name": _INIT, "register_func": register_android_eyes_inbox_init},
        {"name": _STATUS, "register_func": register_android_eyes_inbox_status},
        {"name": _DROP_TEXT, "register_func": register_android_eyes_inbox_drop_text},
        {"name": _DROP_URL, "register_func": register_android_eyes_inbox_drop_url},
        {"name": _STAGE_FILE, "register_func": register_android_eyes_inbox_stage_file},
        {"name": _SCAN, "register_func": register_android_eyes_inbox_scan},
        {"name": _EXAMPLES, "register_func": register_android_eyes_inbox_examples},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [
        _DOCTOR,
        _INIT,
        _STATUS,
        _DROP_TEXT,
        _DROP_URL,
        _STAGE_FILE,
        _SCAN,
        _EXAMPLES,
    ]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
