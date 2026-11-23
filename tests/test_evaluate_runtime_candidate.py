from __future__ import annotations

import copy
import json
import pathlib
import subprocess
import sys

import pytest

from scripts import evaluate_runtime_candidate

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "baselines" / "runtime-adoption-policy-v1.json"
ASSESSMENT_PATH = (
    REPO_ROOT
    / "evidence"
    / "benchmarks"
    / "pax-v1-adoption-assessment-20261122.json"
)
SCRIPT = REPO_ROOT / "scripts" / "evaluate_runtime_candidate.py"


def load(path: pathlib.Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def passing_assessment() -> tuple[dict[str, object], dict[str, object]]:
    policy = load(POLICY_PATH)
    assessment = load(ASSESSMENT_PATH)
    gates = assessment["gates"]
    assert isinstance(gates, dict)
    for gate_id in gates:
        gates[gate_id] = {
            "status": "pass",
            "evidence": [f"receipt:{gate_id}"],
            "note": "Measured and accepted for this fixture.",
        }
    return policy, assessment


def test_real_pax_candidate_is_refused():
    receipt = evaluate_runtime_candidate.evaluate(
        load(POLICY_PATH), load(ASSESSMENT_PATH)
    )

    assert receipt["qualified"] is False
    assert receipt["decision"] == "refuse"
    assert receipt["counts"] == {"fail": 5, "pass": 0, "unmeasured": 7}


def test_every_evidence_backed_gate_must_pass():
    policy, assessment = passing_assessment()

    receipt = evaluate_runtime_candidate.evaluate(policy, assessment)

    assert receipt["qualified"] is True
    assert receipt["decision"] == "qualify"
    assert receipt["counts"] == {"fail": 0, "pass": 12, "unmeasured": 0}


def test_unmeasured_gate_fails_closed():
    policy, assessment = passing_assessment()
    gates = assessment["gates"]
    assert isinstance(gates, dict)
    gates["startup-budget"] = {
        "status": "unmeasured",
        "evidence": [],
        "note": "Not measured.",
    }

    receipt = evaluate_runtime_candidate.evaluate(policy, assessment)

    assert receipt["qualified"] is False
    assert receipt["decision"] == "refuse"


def test_passing_gate_requires_evidence():
    policy, assessment = passing_assessment()
    gates = assessment["gates"]
    assert isinstance(gates, dict)
    gate = gates["minimal-core"]
    assert isinstance(gate, dict)
    gate["evidence"] = []

    with pytest.raises(
        evaluate_runtime_candidate.AssessmentError,
        match="passing gate minimal-core requires evidence",
    ):
        evaluate_runtime_candidate.evaluate(policy, assessment)


def test_missing_or_unexpected_gates_are_invalid():
    policy, assessment = passing_assessment()
    gates = assessment["gates"]
    assert isinstance(gates, dict)
    del gates["minimal-core"]
    gates["marketing-vibes"] = {
        "status": "pass",
        "evidence": ["shiny"],
        "note": "This is not an engineering gate.",
    }

    with pytest.raises(evaluate_runtime_candidate.AssessmentError) as error:
        evaluate_runtime_candidate.evaluate(policy, assessment)

    assert "missing gates: minimal-core" in str(error.value)
    assert "unexpected gates: marketing-vibes" in str(error.value)


def test_cli_refuses_pax_with_machine_readable_receipt():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 1, completed.stderr
    receipt = json.loads(completed.stdout)
    assert receipt["candidate_id"] == "code-puppy-1.0.0rc1-pax"
    assert receipt["qualified"] is False
    assert receipt["decision"] == "refuse"


def test_cli_reports_malformed_assessment_as_invalid(tmp_path):
    malformed = copy.deepcopy(load(ASSESSMENT_PATH))
    malformed["gates"] = []
    assessment_path = tmp_path / "malformed.json"
    assessment_path.write_text(json.dumps(malformed), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--assessment", str(assessment_path)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 2
    receipt = json.loads(completed.stdout)
    assert receipt["decision"] == "invalid"
    assert receipt["qualified"] is False
