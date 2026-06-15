"""The Kernel: durable, contract-typed shared-memory substrate.

SQLite-backed so execution state survives a crash and the Orchestra Agent can
RESUME rather than restart. Access is through defined operations only - never a
free-for-all blackboard. Stores intents, tasks, observations, and results.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any


class Kernel:
    def __init__(self, db_path: str) -> None:
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS intents(
                intent_id TEXT PRIMARY KEY, status TEXT, json TEXT);
            CREATE TABLE IF NOT EXISTS tasks(
                task_id TEXT PRIMARY KEY, intent_id TEXT, status TEXT, json TEXT);
            CREATE TABLE IF NOT EXISTS observations(
                observation_id TEXT PRIMARY KEY, intent_id TEXT, task_id TEXT,
                json TEXT, ts TEXT);
            CREATE TABLE IF NOT EXISTS results(
                result_id TEXT PRIMARY KEY, intent_id TEXT, status TEXT, json TEXT);
            """
        )
        self.db.commit()

    # ---- intents ----
    def save_intent(self, intent: dict[str, Any]) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO intents(intent_id,status,json) VALUES(?,?,?)",
            (intent["intent_id"], intent["status"], json.dumps(intent)),
        )
        self.db.commit()

    def get_intent(self, intent_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT json FROM intents WHERE intent_id=?", (intent_id,)
        ).fetchone()
        return json.loads(row["json"]) if row else None

    def set_intent_status(self, intent_id: str, status: str) -> None:
        intent = self.get_intent(intent_id)
        if intent:
            intent["status"] = status
            self.save_intent(intent)

    # ---- tasks ----
    def save_task(self, task: dict[str, Any]) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO tasks(task_id,intent_id,status,json) "
            "VALUES(?,?,?,?)",
            (task["task_id"], task["intent_id"], task["status"], json.dumps(task)),
        )
        self.db.commit()

    def get_tasks(self, intent_id: str) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT json FROM tasks WHERE intent_id=? ORDER BY task_id", (intent_id,)
        ).fetchall()
        return [json.loads(r["json"]) for r in rows]

    # ---- observations ----
    def add_observation(self, obs: dict[str, Any]) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO observations"
            "(observation_id,intent_id,task_id,json,ts) VALUES(?,?,?,?,?)",
            (obs["observation_id"], obs["intent_id"], obs.get("task_id"),
             json.dumps(obs), obs["ts"]),
        )
        self.db.commit()

    def get_observations(self, intent_id: str) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT json FROM observations WHERE intent_id=? ORDER BY ts, observation_id",
            (intent_id,),
        ).fetchall()
        return [json.loads(r["json"]) for r in rows]

    # ---- results ----
    def save_result(self, result: dict[str, Any]) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO results(result_id,intent_id,status,json) "
            "VALUES(?,?,?,?)",
            (result["result_id"], result["intent_id"], result["status"],
             json.dumps(result)),
        )
        self.db.commit()

    def get_result(self, intent_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT json FROM results WHERE intent_id=?", (intent_id,)
        ).fetchone()
        return json.loads(row["json"]) if row else None
