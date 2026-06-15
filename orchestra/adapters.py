"""Execution adapters (L3) + a registry.

An adapter wraps a capability behind one uniform contract: run(task) -> result.
The Orchestra Agent does not care which adapter it is - DroidPuppy, a broker
MCP, cloud, TV - they all look the same from above. This is what lets L3 be
pluralized instead of welded to Android.

For the vertical slice we ship one real, idempotent adapter: WatchlistAdapter.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Protocol


class Adapter(Protocol):
    name: str

    def run(self, task: dict[str, Any]) -> dict[str, Any]:
        """Return {"status": "succeeded"|"failed", "outputs": {...}, "error": {...}?}."""
        ...


class WatchlistAdapter:
    """Real, idempotent capability: add an option contract to a watchlist.

    Idempotent by design (side_effect_class = idempotent): adding the same
    contract twice is a no-op, so retry/resume is always safe.
    """

    name = "watchlist"

    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS watchlist(key TEXT PRIMARY KEY, json TEXT)"
        )
        self.db.commit()

    def run(self, task: dict[str, Any]) -> dict[str, Any]:
        ins = task.get("inputs", {})
        key = f"{ins.get('symbol')}|{ins.get('exp')}|{ins.get('strike')}|{ins.get('right')}"
        existing = self.db.execute(
            "SELECT 1 FROM watchlist WHERE key=?", (key,)
        ).fetchone()
        self.db.execute(
            "INSERT OR REPLACE INTO watchlist(key,json) VALUES(?,?)",
            (key, json.dumps(ins)),
        )
        self.db.commit()
        return {
            "status": "succeeded",
            "outputs": {"watchlist_key": key, "already_present": bool(existing)},
        }


class Registry:
    def __init__(self) -> None:
        self._adapters: dict[str, Adapter] = {}

    def register(self, adapter: Adapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> Adapter | None:
        return self._adapters.get(name)
