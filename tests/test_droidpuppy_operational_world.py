from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_DIR = REPO_ROOT / "code_puppy" / "plugins" / "droidpuppy_operational_world"
SPEC = importlib.util.spec_from_file_location(
    "droidpuppy_operational_world_tooling",
    MODULE_DIR / "tooling.py",
    submodule_search_locations=[str(MODULE_DIR)],
)
world_tooling = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = world_tooling
SPEC.loader.exec_module(world_tooling)


def test_contract_schemas_parse_and_match_runtime_versions():
    contract_dir = REPO_ROOT / "contracts" / "v1"
    for name in (
        "droidpuppy_world_spec.schema.json",
        "droidpuppy_world_state.schema.json",
        "droidpuppy_world_event.schema.json",
    ):
        schema = json.loads((contract_dir / name).read_text())
        assert schema["$schema"].startswith("https://json-schema.org/")

    assert world_tooling.default_spec()["schema_version"] == "droidpuppy.world_spec.v1"


def test_world_init_materializes_default_entities_and_stream(tmp_path):
    result = world_tooling.droidpuppy_world_init(root=str(tmp_path), overwrite=True)

    assert result["success"] is True
    assert result["state"]["entity_count"] >= 3
    assert (tmp_path / "world_spec.json").is_file()
    assert (tmp_path / "world_state.json").is_file()
    assert (tmp_path / "stream.jsonl").is_file()
    assert "world.initialized" in (tmp_path / "stream.jsonl").read_text()


def test_queued_note_advances_on_tick_and_is_replayable(tmp_path):
    world_tooling.droidpuppy_world_init(root=str(tmp_path), overwrite=True)
    queued = world_tooling.droidpuppy_world_submit_action(
        root=str(tmp_path),
        action_type="note",
        payload_json=json.dumps({"message": "phone survived the tick"}),
    )

    assert queued["success"] is True
    tick = world_tooling.droidpuppy_world_tick(root=str(tmp_path))

    assert tick["success"] is True
    assert tick["tick"] == 1
    assert "action.accepted" in tick["event_types"]
    assert "world.note" in tick["event_types"]
    assert tick["queued_action_count"] == 0
    stream_text = (tmp_path / "stream.jsonl").read_text()
    assert queued["action"]["action_id"] in stream_text
    assert "world.tick.completed" in stream_text


def test_destructive_action_is_approval_gated_and_consequence_fires(tmp_path):
    world_tooling.droidpuppy_world_init(root=str(tmp_path), overwrite=True)
    world_tooling.droidpuppy_world_submit_action(
        root=str(tmp_path),
        action_type="shell.exec",
        payload_json=json.dumps({"command": "rm -rf /tmp/nope"}),
    )

    tick = world_tooling.droidpuppy_world_tick(root=str(tmp_path))

    assert "approval.required" in tick["event_types"]
    assert "consequence.approval_gate" in tick["event_types"]
    perception = world_tooling.droidpuppy_world_perceive(
        root=str(tmp_path),
        viewer="operator",
    )
    entities = perception["perception"]["entities"]
    approvals = [entity for entity in entities.values() if entity["type"] == "approval"]
    assert approvals
    assert approvals[0]["properties"]["status"] == "pending"


def test_mark_entity_sets_property_deterministically(tmp_path):
    world_tooling.droidpuppy_world_init(root=str(tmp_path), overwrite=True)
    world_tooling.droidpuppy_world_submit_action(
        root=str(tmp_path),
        action_type="mark_entity",
        target="device",
        payload_json=json.dumps({"property": "status", "value": "healthy"}),
    )

    tick = world_tooling.droidpuppy_world_tick(root=str(tmp_path))
    perception = world_tooling.droidpuppy_world_perceive(root=str(tmp_path))

    assert "entity.property_set" in tick["event_types"]
    assert (
        perception["perception"]["entities"]["device"]["properties"]["status"]
        == "healthy"
    )


def test_worker_perception_filters_entities_and_hidden_properties(tmp_path):
    spec = world_tooling.default_spec()
    spec["entities"].append(
        {
            "id": "secret_app",
            "type": "app",
            "properties": {"secret": "nope", "status": "installed"},
        }
    )
    spec["entities"].append(
        {
            "id": "worker_task",
            "type": "task",
            "properties": {"secret": "hide me", "status": "pending"},
        }
    )
    world_tooling.droidpuppy_world_init(
        root=str(tmp_path),
        spec_json=json.dumps(spec),
        overwrite=True,
    )

    view = world_tooling.droidpuppy_world_perceive(root=str(tmp_path), viewer="worker")
    entities = view["perception"]["entities"]

    assert "secret_app" not in entities
    assert "worker_task" in entities
    assert "secret" not in entities["worker_task"]["properties"]


def _fake_android_capabilities():
    return {
        "success": True,
        "schema_version": "android.capabilities.v1",
        "device": {
            "manufacturer": "PuppyCorp",
            "model": "ButcherPhone",
            "android_version": "15",
            "sdk": "35",
            "abi": "arm64-v8a",
            "platform": "sharpedge",
        },
        "commands": {"am": "/system/bin/am", "pm": "/system/bin/pm", "missing": ""},
        "capability_flags": {"android_native_available": True, "arm64": True},
        "graphics": {"adreno_or_qualcomm_likely": True},
        "security": {
            "keystore_service_visible": True,
            "gatekeeper_service_visible": True,
            "native_keystore_bridge_required": True,
        },
        "recommended_lanes": ["trust_lane", "event_lane"],
    }


def test_reconcile_can_load_sibling_android_native_tooling():
    module = world_tooling.reconcile_android_world.__globals__[
        "_load_android_native_tooling"
    ]()

    assert hasattr(module, "droidpuppy_android_capabilities")


def test_reconcile_android_updates_world_entities(tmp_path):
    world_tooling.droidpuppy_world_init(root=str(tmp_path), overwrite=True)

    result = world_tooling.droidpuppy_world_reconcile_android(
        root=str(tmp_path),
        capabilities_json=json.dumps(_fake_android_capabilities()),
    )
    view = world_tooling.droidpuppy_world_perceive(
        root=str(tmp_path), viewer="operator"
    )
    entities = view["perception"]["entities"]

    assert result["success"] is True
    assert result["summary"]["command_entities"] == 2
    assert result["summary"]["lane_entities"] == 2
    assert entities["device"]["properties"]["model"] == "ButcherPhone"
    assert entities["android-command-am"]["type"] == "android_command"
    assert entities["lane-trust_lane"]["properties"]["status"] == "recommended"
    assert "android.reconciled" in (tmp_path / "stream.jsonl").read_text()


def test_reconcile_android_dry_run_does_not_write_state(tmp_path):
    world_tooling.droidpuppy_world_init(root=str(tmp_path), overwrite=True)
    before = json.loads((tmp_path / "world_state.json").read_text())

    result = world_tooling.droidpuppy_world_reconcile_android(
        root=str(tmp_path),
        capabilities_json=json.dumps(_fake_android_capabilities()),
        dry_run=True,
    )
    after = json.loads((tmp_path / "world_state.json").read_text())

    assert result["success"] is True
    assert result["state_written"] is False
    assert before == after


def test_replay_reconstructs_tick_and_processed_actions(tmp_path):
    world_tooling.droidpuppy_world_init(root=str(tmp_path), overwrite=True)
    world_tooling.droidpuppy_world_submit_action(
        root=str(tmp_path),
        action_type="mark_entity",
        target="device",
        payload_json=json.dumps({"property": "status", "value": "replayed"}),
    )
    world_tooling.droidpuppy_world_tick(root=str(tmp_path))

    replay = world_tooling.droidpuppy_world_replay(root=str(tmp_path))

    assert replay["success"] is True
    assert replay["replayed_state"]["tick"] == 1
    assert replay["replayed_state"]["queued_action_count"] == 0
    assert replay["replayed_state"]["processed_action_count"] == 1
    assert replay["event_counts"]["entity.property_set"] == 1


def test_replay_can_rewrite_state_from_stream(tmp_path):
    world_tooling.droidpuppy_world_init(root=str(tmp_path), overwrite=True)
    world_tooling.droidpuppy_world_submit_action(root=str(tmp_path), action_type="note")
    world_tooling.droidpuppy_world_tick(root=str(tmp_path))
    (tmp_path / "world_state.json").write_text("{}")

    replay = world_tooling.droidpuppy_world_replay(root=str(tmp_path), write_state=True)
    restored = json.loads((tmp_path / "world_state.json").read_text())

    assert replay["state_written"] is True
    assert restored["tick"] == 1
    assert restored["processed_action_ids"]


def test_dry_run_tick_does_not_write_state(tmp_path):
    world_tooling.droidpuppy_world_init(root=str(tmp_path), overwrite=True)
    world_tooling.droidpuppy_world_submit_action(root=str(tmp_path), action_type="note")
    before = json.loads((tmp_path / "world_state.json").read_text())

    tick = world_tooling.droidpuppy_world_tick(root=str(tmp_path), dry_run=True)
    after = json.loads((tmp_path / "world_state.json").read_text())

    assert tick["success"] is True
    assert tick["state_written"] is False
    assert before == after
