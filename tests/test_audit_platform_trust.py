from __future__ import annotations

import importlib.util
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "audit_platform_trust.py"
SPEC = importlib.util.spec_from_file_location("audit_platform_trust", SCRIPT)
audit_platform_trust = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = audit_platform_trust
SPEC.loader.exec_module(audit_platform_trust)


def fake_runner(properties: dict[str, str], features: set[str]):
    def run(args: list[str]):
        if args[:1] == ["getprop"]:
            return 0, properties.get(args[1], ""), ""
        if args == ["pm", "list", "features"]:
            return 0, "\n".join(f"feature:{item}" for item in sorted(features)), ""
        if args[-1:] == ["--list-devices"]:
            return 0, "Available devices:\n  (none)", ""
        return 127, "", "unavailable"

    return run


def secure_properties() -> dict[str, str]:
    return {
        "ro.boot.verifiedbootstate": "green",
        "ro.boot.flash.locked": "1",
        "ro.boot.vbmeta.device_state": "locked",
        "ro.crypto.state": "encrypted",
        "ro.build.type": "user",
        "ro.product.manufacturer": "example",
        "ro.product.model": "phone",
        "ro.soc.manufacturer": "QTI",
        "ro.soc.model": "SM8750",
        "ro.product.cpu.abi": "arm64-v8a",
        "ro.build.version.release": "17",
    }


def test_secure_platform_and_disabled_mcp_pass(tmp_path, monkeypatch):
    config = tmp_path / "puppy.cfg"
    config.write_text("disable_mcp_servers = true\n")
    features = {
        "android.hardware.strongbox_keystore",
        "android.hardware.keystore.app_attest_key",
        "android.hardware.vulkan.compute",
    }
    monkeypatch.setattr(audit_platform_trust.shutil, "which", lambda _: None)

    receipt = audit_platform_trust.collect_posture(
        runner=fake_runner(secure_properties(), features),
        config_path=config,
        library_roots=(tmp_path,),
    )

    by_name = {item["name"]: item for item in receipt["checks"]}
    assert by_name["verified_boot"]["status"] == "pass"
    assert by_name["bootloader_lock"]["status"] == "pass"
    assert by_name["hardware_trust_root"]["status"] == "pass"
    assert by_name["mcp_default"]["status"] == "pass"
    assert receipt["claims"]["proves_uncorruptable"] is False
    assert receipt["claims"]["proves_not_rooted"] is False


def test_enabled_mcp_and_unlocked_boot_warn(tmp_path, monkeypatch):
    config = tmp_path / "puppy.cfg"
    config.write_text("disable_mcp_servers = false\n")
    properties = secure_properties()
    properties["ro.boot.flash.locked"] = "0"
    monkeypatch.setattr(audit_platform_trust.shutil, "which", lambda _: None)

    receipt = audit_platform_trust.collect_posture(
        runner=fake_runner(properties, set()),
        config_path=config,
        library_roots=(tmp_path,),
    )

    by_name = {item["name"]: item for item in receipt["checks"]}
    assert by_name["bootloader_lock"]["status"] == "warn"
    assert by_name["hardware_trust_root"]["status"] == "warn"
    assert by_name["mcp_default"]["status"] == "warn"


def test_missing_properties_are_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_platform_trust.shutil, "which", lambda _: None)

    receipt = audit_platform_trust.collect_posture(
        runner=fake_runner({}, set()),
        config_path=tmp_path / "missing.cfg",
        library_roots=(tmp_path,),
    )

    by_name = {item["name"]: item for item in receipt["checks"]}
    assert by_name["verified_boot"]["status"] == "unknown"
    assert by_name["storage_encryption"]["status"] == "unknown"
    assert by_name["mcp_default"]["status"] == "unknown"


def test_config_parser_never_reads_other_values(tmp_path):
    config = tmp_path / "puppy.cfg"
    config.write_text(
        "api_key = do-not-return-this\n"
        "disable_mcp_servers = false\n"
        "password = also-do-not-return\n"
    )

    assert (
        audit_platform_trust.parse_boolean_config(config, "disable_mcp_servers")
        is False
    )
