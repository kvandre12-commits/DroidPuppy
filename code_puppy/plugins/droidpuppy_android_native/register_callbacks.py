"""Register DroidPuppy Android-native surface tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    droidpuppy_android_approval_receipt as approval_receipt_impl,
    droidpuppy_android_capabilities as capabilities_impl,
    droidpuppy_android_event_publish as event_publish_impl,
    droidpuppy_android_verify_approval_receipt as verify_approval_receipt_impl,
)

_CAPABILITIES = "droidpuppy_android_capabilities"
_EVENT_PUBLISH = "droidpuppy_android_event_publish"
_APPROVAL_RECEIPT = "droidpuppy_android_approval_receipt"
_VERIFY_APPROVAL_RECEIPT = "droidpuppy_android_verify_approval_receipt"


def register_droidpuppy_android_capabilities(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_android_capabilities(context: RunContext) -> dict[str, Any]:
        """Probe Android-native hardware/security/media/event surfaces.

        Returns an ``android.capabilities.v1`` report. This is read-only.
        """
        del context
        return capabilities_impl()


def register_droidpuppy_android_event_publish(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_android_event_publish(
        context: RunContext,
        event_type: str,
        payload_json: str = "{}",
        topic: str = "android.native",
        source: str = "droidpuppy.android_native",
        output_path: str = "outputs/droidpuppy_android_events.jsonl",
        publish_to_project_os_bus: bool = True,
    ) -> dict[str, Any]:
        """Append an ``android.event_bridge.v1`` event and best-effort publish it.

        ``payload_json`` must decode to a JSON object. The event is always
        appended to JSONL first, then optionally published to the Project OS bus.
        """
        del context
        return event_publish_impl(
            event_type=event_type,
            payload_json=payload_json,
            topic=topic,
            source=source,
            output_path=output_path,
            publish_to_project_os_bus=publish_to_project_os_bus,
        )


def register_droidpuppy_android_approval_receipt(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_android_approval_receipt(
        context: RunContext,
        principal_id: str,
        capability: str,
        action: str,
        reason: str,
        risk_tier: str = "review_required",
        ttl_seconds: int = 60,
        nonce: str = "",
        signing_backend: str = "local-hmac-dev",
    ) -> dict[str, Any]:
        """Create an ``android.approval_receipt.v1`` development receipt.

        The Termux bridge currently returns a local HMAC development signature,
        not a hardware-backed Android Keystore signature. Use this envelope as
        the contract for the native Keystore signer.
        """
        del context
        return approval_receipt_impl(
            principal_id=principal_id,
            capability=capability,
            action=action,
            reason=reason,
            risk_tier=risk_tier,
            ttl_seconds=ttl_seconds,
            nonce=nonce,
            signing_backend=signing_backend,
        )


def register_droidpuppy_android_verify_approval_receipt(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_android_verify_approval_receipt(
        context: RunContext,
        receipt_json: str,
        require_hardware_backed: bool = False,
    ) -> dict[str, Any]:
        """Verify an ``android.approval_receipt.v1`` development receipt.

        Local HMAC development receipts can be verified in Termux. Hardware-backed
        Android Keystore receipts require the future native verifier bridge.
        """
        del context
        return verify_approval_receipt_impl(
            receipt_json=receipt_json,
            require_hardware_backed=require_hardware_backed,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {
            "name": _CAPABILITIES,
            "register_func": register_droidpuppy_android_capabilities,
        },
        {
            "name": _EVENT_PUBLISH,
            "register_func": register_droidpuppy_android_event_publish,
        },
        {
            "name": _APPROVAL_RECEIPT,
            "register_func": register_droidpuppy_android_approval_receipt,
        },
        {
            "name": _VERIFY_APPROVAL_RECEIPT,
            "register_func": register_droidpuppy_android_verify_approval_receipt,
        },
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_CAPABILITIES, _EVENT_PUBLISH, _APPROVAL_RECEIPT, _VERIFY_APPROVAL_RECEIPT]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
