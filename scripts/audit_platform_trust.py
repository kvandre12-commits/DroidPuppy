#!/usr/bin/env python3
"""Read-only Android trust and acceleration posture audit."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

CommandRunner = Callable[[list[str]], tuple[int, str, str]]


def run_command(args: list[str]) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def getprop(name: str, runner: CommandRunner) -> str:
    code, stdout, _ = runner(["getprop", name])
    return stdout if code == 0 else ""


def check(name: str, status: str, evidence: str) -> dict[str, str]:
    return {"name": name, "status": status, "evidence": evidence}


def expected_check(
    name: str,
    actual: str,
    expected: set[str],
    *,
    pass_evidence: str,
) -> dict[str, str]:
    if not actual:
        return check(name, "unknown", "property unavailable")
    if actual.lower() in expected:
        return check(name, "pass", pass_evidence)
    return check(name, "warn", f"unexpected state: {actual}")


def parse_boolean_config(path: Path, key: str) -> bool | None:
    if not path.is_file():
        return None
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        candidate, value = map(str.strip, stripped.split("=", 1))
        if candidate != key:
            continue
        normalized = value.lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
        return None
    return None


def _feature_set(runner: CommandRunner) -> set[str]:
    code, stdout, _ = runner(["pm", "list", "features"])
    if code != 0:
        return set()
    return {
        line.removeprefix("feature:").split("=", 1)[0]
        for line in stdout.splitlines()
        if line.startswith("feature:")
    }


def _existing_paths(paths: tuple[Path, ...]) -> list[str]:
    return [path.name for path in paths if path.is_file()]


def _llama_devices(runner: CommandRunner) -> tuple[str, list[str]]:
    llama_cli = shutil.which("llama-cli")
    if not llama_cli:
        return "unavailable", []
    code, stdout, stderr = runner([llama_cli, "--list-devices"])
    text = "\n".join(part for part in (stdout, stderr) if part)
    devices = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and line.strip() not in {"Available devices:", "(none)"}
    ]
    if code != 0:
        return "unknown", devices
    return ("available" if devices else "none"), devices


def collect_posture(
    *,
    runner: CommandRunner = run_command,
    config_path: Path | None = None,
    library_roots: tuple[Path, ...] = (Path("/vendor/lib64"), Path("/system/lib64")),
) -> dict[str, Any]:
    config_path = config_path or Path.home() / ".code_puppy" / "puppy.cfg"
    checks: list[dict[str, str]] = []

    checks.append(
        expected_check(
            "verified_boot",
            getprop("ro.boot.verifiedbootstate", runner),
            {"green"},
            pass_evidence="Android Verified Boot reports green",
        )
    )
    checks.append(
        expected_check(
            "bootloader_lock",
            getprop("ro.boot.flash.locked", runner),
            {"1", "true"},
            pass_evidence="bootloader reports locked",
        )
    )
    checks.append(
        expected_check(
            "vbmeta_state",
            getprop("ro.boot.vbmeta.device_state", runner),
            {"locked"},
            pass_evidence="vbmeta device state reports locked",
        )
    )
    checks.append(
        expected_check(
            "storage_encryption",
            getprop("ro.crypto.state", runner),
            {"encrypted"},
            pass_evidence="Android storage reports encrypted",
        )
    )
    checks.append(
        expected_check(
            "production_build",
            getprop("ro.build.type", runner),
            {"user"},
            pass_evidence="Android build type is user",
        )
    )

    features = _feature_set(runner)
    strongbox = "android.hardware.strongbox_keystore" in features
    app_attestation = "android.hardware.keystore.app_attest_key" in features
    checks.append(
        check(
            "hardware_trust_root",
            "pass" if strongbox and app_attestation else "warn",
            "StrongBox and app-attestation features visible"
            if strongbox and app_attestation
            else "StrongBox or app-attestation feature not visible",
        )
    )

    mcp_disabled = parse_boolean_config(config_path, "disable_mcp_servers")
    if mcp_disabled is True:
        checks.append(check("mcp_default", "pass", "MCP servers disabled globally"))
    elif mcp_disabled is False:
        checks.append(check("mcp_default", "warn", "MCP servers globally enabled"))
    else:
        checks.append(check("mcp_default", "unknown", "MCP default not resolved"))

    compute_paths = tuple(
        root / filename
        for root in library_roots
        for filename in (
            "libOpenCL.so",
            "libOpenCL_adreno.so",
            "libvulkan.so",
            "libcuda.so",
        )
    )
    libraries = _existing_paths(compute_paths)
    cuda_present = any(name == "libcuda.so" for name in libraries)
    vulkan_compute = "android.hardware.vulkan.compute" in features
    opencl_present = any(name.startswith("libOpenCL") for name in libraries)
    checks.append(
        check(
            "mobile_compute_surface",
            "pass" if vulkan_compute or opencl_present else "unknown",
            f"vulkan_compute={vulkan_compute}; opencl={opencl_present}; cuda={cuda_present}",
        )
    )

    llama_state, llama_devices = _llama_devices(runner)
    if llama_state == "available":
        checks.append(
            check(
                "local_inference_acceleration",
                "pass",
                f"llama.cpp devices visible: {len(llama_devices)}",
            )
        )
    elif llama_state == "none":
        checks.append(
            check(
                "local_inference_acceleration",
                "warn",
                "llama.cpp reports no accelerator devices",
            )
        )
    else:
        checks.append(
            check(
                "local_inference_acceleration",
                "unknown",
                f"llama.cpp device probe: {llama_state}",
            )
        )

    counts = {
        status: sum(item["status"] == status for item in checks)
        for status in ("pass", "warn", "unknown")
    }
    return {
        "schema_version": 1,
        "audit": "android-platform-trust",
        "read_only": True,
        "claims": {
            "proves_uncorruptable": False,
            "proves_not_rooted": False,
            "performs_exploitation": False,
            "modifies_configuration": False,
        },
        "device_class": {
            "manufacturer": getprop("ro.product.manufacturer", runner),
            "model": getprop("ro.product.model", runner),
            "soc_manufacturer": getprop("ro.soc.manufacturer", runner),
            "soc_model": getprop("ro.soc.model", runner),
            "abi": getprop("ro.product.cpu.abi", runner),
            "android_version": getprop("ro.build.version.release", runner),
        },
        "checks": checks,
        "summary": counts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON receipt path")
    args = parser.parse_args(argv)

    receipt = collect_posture()
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
