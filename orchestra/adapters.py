"""Execution adapters (L3) + a registry.

An adapter wraps a capability behind one uniform contract: run(task) -> result.
The Orchestra Agent does not care which adapter it is - DroidPuppy, a broker
MCP, cloud, TV - they all look the same from above. This is what lets L3 be
pluralized instead of welded to Android.

Ships two adapters: WatchlistAdapter (idempotent local capability) and
DroidPuppyAdapter (real Android device actions via `am`).
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
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


class DroidPuppyAdapter:
    """Wraps real Android device actions via the `am` capability DroidPuppy exposes.

    Supported task types:
      - open_url   : inputs {url, browser?} -> launch a URL (optionally in a
                     specific browser package)
      - launch_app : inputs {package}       -> launch an app by package

    Launching is idempotent-ish (re-launch just refocuses), so retry is safe.
    This is the orchestra reaching into the real device - L3 doing actual work.
    """

    name = "droidpuppy"

    def run(self, task: dict[str, Any]) -> dict[str, Any]:
        am = shutil.which("am")
        if not am:
            return {"status": "failed",
                    "error": {"code": "no_am", "message": "am command not found"}}
        ttype = task.get("type")
        ins = task.get("inputs", {})
        if ttype == "open_url":
            args = [am, "start", "-a", "android.intent.action.VIEW",
                    "-d", ins.get("url", "")]
            if ins.get("browser"):
                args += ["-p", ins["browser"]]
        elif ttype == "launch_app":
            args = [am, "start", "-a", "android.intent.action.MAIN",
                    "-c", "android.intent.category.LAUNCHER",
                    "-p", ins.get("package", "")]
        else:
            return {"status": "failed",
                    "error": {"code": "unknown_type",
                              "message": f"DroidPuppyAdapter cannot do '{ttype}'"}}
        try:
            res = subprocess.run(args, capture_output=True, text=True, timeout=20)
        except Exception as exc:  # noqa: BLE001 - never crash the orchestra
            return {"status": "failed",
                    "error": {"code": "exec_error", "message": str(exc)}}
        ok = res.returncode == 0
        return {
            "status": "succeeded" if ok else "failed",
            "outputs": {"command": " ".join(args), "exit_code": res.returncode,
                        "stdout": res.stdout.strip()[:200]},
            "error": None if ok else {"code": "am_failed",
                                      "message": res.stderr.strip()[:200]},
        }


class MockBrokerAdapter:
    """Stand-in for an irreversible capability (placing a real broker order).

    Marked conceptually irreversible: the Orchestra will gate it behind human
    approval and will NOT auto-retry it on failure. This mock just records the
    'order' and returns a fake order id - but it models the real danger class.
    """

    name = "broker"

    def __init__(self) -> None:
        self.orders: list[dict[str, Any]] = []

    def run(self, task: dict[str, Any]) -> dict[str, Any]:
        order = dict(task.get("inputs", {}))
        order_id = f"ord-{len(self.orders) + 1:04d}"
        self.orders.append({"order_id": order_id, **order})
        return {"status": "succeeded",
                "outputs": {"order_id": order_id, "order": order}}


class Registry:
    def __init__(self) -> None:
        self._adapters: dict[str, Adapter] = {}

    def register(self, adapter: Adapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> Adapter | None:
        return self._adapters.get(name)
