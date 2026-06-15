"""The Orchestra Agent: sole coordinator of execution (the vertical slice).

Implements the eight responsibilities as a real, durable loop:
  1 decompose intent  2 select participants  3 route work  4 manage handoffs
  5 maintain state    6 observe outcomes     7 handle failures/recovery
  8 report results back to the intent layer

Every artifact is validated against the v1 contracts before it is trusted.
State lives in the Kernel, so run() is resumable: re-running it never re-does
completed work. The Orchestra never performs domain analysis and never executes
a capability directly - it only coordinates.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import uuid
from typing import Any

import jsonschema

from adapters import Registry
from kernel import Kernel

_SCHEMAS = ["intent", "task", "handoff", "observation", "result"]


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class OrchestraAgent:
    def __init__(self, kernel: Kernel, registry: Registry, contracts_dir: str) -> None:
        self.k = kernel
        self.reg = registry
        self.schemas = {
            name: json.load(open(os.path.join(contracts_dir, f"{name}.schema.json")))
            for name in _SCHEMAS
        }

    # ---- observability spine (responsibility 6) ----
    def _emit(self, intent_id: str, otype: str, message: str,
              task_id: str | None = None, severity: str = "info") -> None:
        obs = {
            "contract_version": "1.0.0",
            "observation_id": _uid("obs"),
            "intent_id": intent_id,
            "task_id": task_id,
            "type": otype,
            "severity": severity,
            "payload": {"message": message},
            "source_adapter": None,
            "ts": _now(),
        }
        jsonschema.validate(obs, self.schemas["observation"])
        self.k.add_observation(obs)

    # ---- intake: validate + persist (contract-compliant or rejected) ----
    def submit(self, intent: dict[str, Any]) -> str:
        jsonschema.validate(intent, self.schemas["intent"])
        self.k.save_intent(intent)
        self._emit(intent["intent_id"], "progress",
                   f"intent accepted: {intent.get('statement', intent['goal']['type'])}")
        return intent["intent_id"]

    # ---- responsibility 1: structural decomposition (NOT domain analysis) ----
    def _decompose(self, intent: dict[str, Any]) -> list[dict[str, Any]]:
        goal = intent["goal"]
        if goal["type"] == "watchlist_add":
            return [self._make_task(intent, "add_to_watchlist", "watchlist",
                                    goal.get("params", {}), side_effect="idempotent")]
        raise ValueError(f"no decomposition rule for goal type '{goal['type']}'")

    def _make_task(self, intent: dict[str, Any], ttype: str, adapter: str,
                   inputs: dict[str, Any], side_effect: str = "read",
                   depends: list[str] | None = None,
                   requires_approval: bool = False) -> dict[str, Any]:
        task = {
            "contract_version": "1.0.0",
            "task_id": _uid("task"),
            "intent_id": intent["intent_id"],
            "type": ttype,
            "target_adapter": adapter,
            "inputs": inputs,
            "side_effect_class": side_effect,
            "retry_policy": {"max_attempts": 2, "backoff": "fixed",
                             "retry_on": ["transient"]},
            "timeout_ms": 10000,
            "depends_on": depends or [],
            "idempotency_key": f"{intent['intent_id']}:{ttype}",
            "requires_approval": requires_approval,
            "status": "pending",
            "attempts": 0,
        }
        jsonschema.validate(task, self.schemas["task"])
        return task

    # ---- responsibilities 2-7: run the DAG ----
    def run(self, intent_id: str) -> dict[str, Any]:
        intent = self.k.get_intent(intent_id)
        if intent is None:
            raise ValueError(f"unknown intent {intent_id}")

        tasks = self.k.get_tasks(intent_id)
        if not tasks:  # first run -> plan; resume -> tasks already exist
            self.k.set_intent_status(intent_id, "planning")
            tasks = self._decompose(intent)
            for task in tasks:
                self.k.save_task(task)
            self._emit(intent_id, "progress", f"decomposed into {len(tasks)} task(s)")

        self.k.set_intent_status(intent_id, "executing")
        terminal_states = {"succeeded", "failed", "aborted", "compensated"}

        while True:
            tasks = self.k.get_tasks(intent_id)
            done = {t["task_id"] for t in tasks if t["status"] == "succeeded"}
            ready = [
                t for t in tasks
                if t["status"] in ("pending", "ready")
                and all(dep in done for dep in t["depends_on"])
            ]
            if not ready:
                if all(t["status"] in terminal_states for t in tasks):
                    break
                if any(t["status"] == "awaiting_approval" for t in tasks):
                    break  # suspended for human authority
                # a dependency failed: abort what can no longer run
                for t in tasks:
                    if t["status"] in ("pending", "ready"):
                        t["status"] = "aborted"
                        self.k.save_task(t)
                break
            for task in ready:
                self._run_task(intent_id, task)

        return self._finish(intent_id)

    def _run_task(self, intent_id: str, task: dict[str, Any]) -> None:
        # responsibility: human-authority gate
        if task["requires_approval"]:
            task["status"] = "awaiting_approval"
            self.k.save_task(task)
            self._emit(intent_id, "approval_required",
                       f"task '{task['type']}' needs approval before it can run",
                       task_id=task["task_id"], severity="warn")
            return

        # responsibility 2: select participant
        adapter = self.reg.get(task["target_adapter"])
        if adapter is None:
            task["status"] = "failed"
            self.k.save_task(task)
            self._emit(intent_id, "contract_violation",
                       f"no adapter registered named '{task['target_adapter']}'",
                       task_id=task["task_id"], severity="error")
            return

        # responsibility 3: route work
        task["status"] = "running"
        task["attempts"] += 1
        self.k.save_task(task)
        self._emit(intent_id, "progress",
                   f"running '{task['type']}' via {task['target_adapter']} "
                   f"(attempt {task['attempts']})", task_id=task["task_id"])

        try:
            out = adapter.run(task)
        except Exception as exc:  # noqa: BLE001 - adapters must never crash the loop
            out = {"status": "failed",
                   "error": {"code": "adapter_exception", "message": str(exc)}}

        if out.get("status") == "succeeded":
            task["status"] = "succeeded"
            self.k.save_task(task)
            self._emit(intent_id, "progress",
                       f"'{task['type']}' succeeded: {out.get('outputs')}",
                       task_id=task["task_id"])
            return

        # responsibility 7: recovery - retry only if side-effect-safe
        safe_to_retry = task["side_effect_class"] in ("read", "idempotent")
        more_attempts = task["attempts"] <= task["retry_policy"]["max_attempts"]
        if safe_to_retry and more_attempts:
            task["status"] = "ready"
            self.k.save_task(task)
            self._emit(intent_id, "log",
                       f"'{task['type']}' failed; safe to retry, re-queued",
                       task_id=task["task_id"], severity="warn")
        else:
            task["status"] = "failed"
            self.k.save_task(task)
            self._emit(intent_id, "contract_violation",
                       f"'{task['type']}' failed permanently "
                       f"(retry-safe={safe_to_retry})",
                       task_id=task["task_id"], severity="error")

    # ---- responsibility 8: report results back to the intent layer ----
    def _finish(self, intent_id: str) -> dict[str, Any]:
        tasks = self.k.get_tasks(intent_id)
        statuses = [t["status"] for t in tasks]
        if statuses and all(s == "succeeded" for s in statuses):
            status = "success"
        elif any(s == "awaiting_approval" for s in statuses):
            status = "partial"
        elif any(s == "succeeded" for s in statuses):
            status = "partial"
        else:
            status = "failed"

        result = {
            "contract_version": "1.0.0",
            "result_id": _uid("res"),
            "intent_id": intent_id,
            "status": status,
            "outputs": {},
            "task_summary": [
                {"task_id": t["task_id"], "status": t["status"]} for t in tasks
            ],
            "compensations_applied": [],
            "error": None,
            "completed_at": _now(),
        }
        jsonschema.validate(result, self.schemas["result"])
        self.k.save_result(result)
        self.k.set_intent_status(intent_id, "done" if status == "success" else "failed")
        self._emit(intent_id, "progress", f"result reported to intent layer: {status}")
        return result
