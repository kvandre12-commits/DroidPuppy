#!/usr/bin/env python3
"""Evaluate a runtime candidate against a fail-closed adoption policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY = REPO_ROOT / "baselines" / "runtime-adoption-policy-v1.json"
DEFAULT_ASSESSMENT = (
    REPO_ROOT
    / "evidence"
    / "benchmarks"
    / "pax-v1-adoption-assessment-20261122.json"
)


class AssessmentError(ValueError):
    """Raised when a policy or assessment is structurally invalid."""


def load_document(path: Path) -> dict[str, object]:
    """Load one JSON object from ``path``."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssessmentError(f"{path}: document must be a JSON object")
    return data


def _policy_gates(policy: dict[str, object]) -> dict[str, str]:
    gates = policy.get("gates")
    if not isinstance(gates, list) or not gates:
        raise AssessmentError("policy gates must be a non-empty array")

    parsed: dict[str, str] = {}
    for index, gate in enumerate(gates):
        if not isinstance(gate, dict):
            raise AssessmentError(f"policy gate {index} must be an object")
        gate_id = gate.get("id")
        requirement = gate.get("requirement")
        if not isinstance(gate_id, str) or not gate_id:
            raise AssessmentError(f"policy gate {index} has no valid id")
        if gate_id in parsed:
            raise AssessmentError(f"duplicate policy gate: {gate_id}")
        if not isinstance(requirement, str) or not requirement:
            raise AssessmentError(f"policy gate {gate_id} has no requirement")
        parsed[gate_id] = requirement
    return parsed


def evaluate(
    policy: dict[str, object], assessment: dict[str, object]
) -> dict[str, object]:
    """Return a deterministic qualification receipt.

    Every policy gate must exist exactly once in the assessment. Only an
    evidence-backed ``pass`` satisfies a gate. ``fail`` and ``unmeasured`` both
    refuse qualification.
    """
    if policy.get("schema_version") != 1:
        raise AssessmentError("policy schema_version must equal 1")
    if assessment.get("schema_version") != 1:
        raise AssessmentError("assessment schema_version must equal 1")

    policy_id = policy.get("policy_id")
    if not isinstance(policy_id, str) or not policy_id:
        raise AssessmentError("policy_id must be a non-empty string")
    if assessment.get("policy_id") != policy_id:
        raise AssessmentError("assessment policy_id does not match policy")

    for field in ("scope", "expansion_principle"):
        if not isinstance(policy.get(field), str) or not policy[field]:
            raise AssessmentError(f"policy {field} must be a non-empty string")
    does_not_block = policy.get("does_not_block")
    if not isinstance(does_not_block, list) or not does_not_block or not all(
        isinstance(item, str) and item for item in does_not_block
    ):
        raise AssessmentError("policy does_not_block must be a non-empty string array")

    candidate_id = assessment.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id:
        raise AssessmentError("candidate_id must be a non-empty string")

    allowed = policy.get("allowed_statuses")
    if not isinstance(allowed, list) or not allowed or not all(
        isinstance(status, str) for status in allowed
    ):
        raise AssessmentError("allowed_statuses must be a non-empty string array")
    allowed_statuses = set(allowed)
    if "pass" not in allowed_statuses:
        raise AssessmentError("allowed_statuses must include pass")

    required = _policy_gates(policy)
    submitted = assessment.get("gates")
    if not isinstance(submitted, dict):
        raise AssessmentError("assessment gates must be an object")

    missing = sorted(set(required) - set(submitted))
    unexpected = sorted(set(submitted) - set(required))
    if missing or unexpected:
        details = []
        if missing:
            details.append("missing gates: " + ", ".join(missing))
        if unexpected:
            details.append("unexpected gates: " + ", ".join(unexpected))
        raise AssessmentError("; ".join(details))

    results = []
    counts = {status: 0 for status in sorted(allowed_statuses)}
    for gate_id, requirement in required.items():
        entry = submitted[gate_id]
        if not isinstance(entry, dict):
            raise AssessmentError(f"assessment gate {gate_id} must be an object")
        status = entry.get("status")
        evidence = entry.get("evidence")
        note = entry.get("note")
        if status not in allowed_statuses:
            raise AssessmentError(f"assessment gate {gate_id} has invalid status")
        if not isinstance(evidence, list) or not all(
            isinstance(item, str) and item for item in evidence
        ):
            raise AssessmentError(f"assessment gate {gate_id} has invalid evidence")
        if status == "pass" and not evidence:
            raise AssessmentError(f"passing gate {gate_id} requires evidence")
        if not isinstance(note, str) or not note:
            raise AssessmentError(f"assessment gate {gate_id} requires a note")
        counts[status] += 1
        results.append(
            {
                "id": gate_id,
                "requirement": requirement,
                "status": status,
                "evidence": evidence,
                "note": note,
            }
        )

    qualified = all(result["status"] == "pass" for result in results)
    return {
        "schema_version": 1,
        "policy_id": policy_id,
        "policy_scope": policy.get("scope"),
        "expansion_principle": policy.get("expansion_principle"),
        "does_not_block": does_not_block,
        "candidate_id": candidate_id,
        "qualified": qualified,
        "decision": "qualify" if qualified else "refuse",
        "counts": counts,
        "source_identity": assessment.get("source_identity"),
        "gates": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--assessment", type=Path, default=DEFAULT_ASSESSMENT)
    args = parser.parse_args(argv)

    try:
        receipt = evaluate(
            load_document(args.policy), load_document(args.assessment)
        )
    except (OSError, json.JSONDecodeError, AssessmentError) as exc:
        receipt = {
            "schema_version": 1,
            "qualified": False,
            "decision": "invalid",
            "errors": [str(exc)],
        }
        code = 2
    else:
        code = 0 if receipt["qualified"] else 1

    print(json.dumps(receipt, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
