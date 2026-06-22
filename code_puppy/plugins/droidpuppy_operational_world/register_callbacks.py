"""Register DroidPuppy operational-world tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    droidpuppy_world_doctor as world_doctor_impl,
    droidpuppy_world_examples as world_examples_impl,
    droidpuppy_world_init as world_init_impl,
    droidpuppy_world_perceive as world_perceive_impl,
    droidpuppy_world_reconcile_android as world_reconcile_android_impl,
    droidpuppy_world_replay as world_replay_impl,
    droidpuppy_world_scan_consequences as world_scan_consequences_impl,
    droidpuppy_world_submit_action as world_submit_action_impl,
    droidpuppy_world_tick as world_tick_impl,
)

_DOCTOR = "droidpuppy_world_doctor"
_INIT = "droidpuppy_world_init"
_SUBMIT_ACTION = "droidpuppy_world_submit_action"
_TICK = "droidpuppy_world_tick"
_PERCEIVE = "droidpuppy_world_perceive"
_SCAN = "droidpuppy_world_scan_consequences"
_RECONCILE_ANDROID = "droidpuppy_world_reconcile_android"
_REPLAY = "droidpuppy_world_replay"
_EXAMPLES = "droidpuppy_world_examples"


def register_droidpuppy_world_doctor(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_world_doctor(
        context: RunContext, root: str = ""
    ) -> dict[str, Any]:
        """Inspect operational-world readiness and durable state files."""
        del context
        return world_doctor_impl(root=root)


def register_droidpuppy_world_init(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_world_init(
        context: RunContext,
        root: str = "",
        spec_json: str = "",
        spec_path: str = "",
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Initialize the operational world from a declarative JSON spec."""
        del context
        return world_init_impl(
            root=root,
            spec_json=spec_json,
            spec_path=spec_path,
            overwrite=overwrite,
        )


def register_droidpuppy_world_submit_action(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_world_submit_action(
        context: RunContext,
        action_type: str,
        actor: str = "operator",
        target: str = "",
        payload_json: str = "{}",
        root: str = "",
    ) -> dict[str, Any]:
        """Queue an operational-world action for the next tick."""
        del context
        return world_submit_action_impl(
            action_type=action_type,
            actor=actor,
            target=target,
            payload_json=payload_json,
            root=root,
        )


def register_droidpuppy_world_tick(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_world_tick(
        context: RunContext,
        root: str = "",
        max_actions: int = 10,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Advance the operational world one deterministic tick."""
        del context
        return world_tick_impl(root=root, max_actions=max_actions, dry_run=dry_run)


def register_droidpuppy_world_perceive(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_world_perceive(
        context: RunContext,
        viewer: str = "operator",
        root: str = "",
        stream_tail: int = 20,
    ) -> dict[str, Any]:
        """Return a viewer-filtered operational-world perception packet."""
        del context
        return world_perceive_impl(viewer=viewer, root=root, stream_tail=stream_tail)


def register_droidpuppy_world_scan_consequences(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_world_scan_consequences(
        context: RunContext,
        root: str = "",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Run the declarative consequence scanner against current state/events."""
        del context
        return world_scan_consequences_impl(root=root, dry_run=dry_run)


def register_droidpuppy_world_reconcile_android(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_world_reconcile_android(
        context: RunContext,
        root: str = "",
        capabilities_json: str = "",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Reconcile Android capability facts into operational-world entities."""
        del context
        return world_reconcile_android_impl(
            root=root,
            capabilities_json=capabilities_json,
            dry_run=dry_run,
        )


def register_droidpuppy_world_replay(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_world_replay(
        context: RunContext,
        root: str = "",
        write_state: bool = False,
    ) -> dict[str, Any]:
        """Replay stream.jsonl into a reconstructed operational-world state summary."""
        del context
        return world_replay_impl(root=root, write_state=write_state)


def register_droidpuppy_world_examples(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_world_examples(context: RunContext) -> dict[str, Any]:
        """Show operational-world usage examples."""
        del context
        return world_examples_impl()


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_droidpuppy_world_doctor},
        {"name": _INIT, "register_func": register_droidpuppy_world_init},
        {
            "name": _SUBMIT_ACTION,
            "register_func": register_droidpuppy_world_submit_action,
        },
        {"name": _TICK, "register_func": register_droidpuppy_world_tick},
        {"name": _PERCEIVE, "register_func": register_droidpuppy_world_perceive},
        {"name": _SCAN, "register_func": register_droidpuppy_world_scan_consequences},
        {
            "name": _RECONCILE_ANDROID,
            "register_func": register_droidpuppy_world_reconcile_android,
        },
        {"name": _REPLAY, "register_func": register_droidpuppy_world_replay},
        {"name": _EXAMPLES, "register_func": register_droidpuppy_world_examples},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [
        _DOCTOR,
        _INIT,
        _SUBMIT_ACTION,
        _TICK,
        _PERCEIVE,
        _SCAN,
        _RECONCILE_ANDROID,
        _REPLAY,
        _EXAMPLES,
    ]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
