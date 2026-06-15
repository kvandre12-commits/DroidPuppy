"""Pluggable planners - domain decomposition lives here, not in the Orchestra.

This is the fix for the review's sharpest critique: the Orchestra must do
STRUCTURAL orchestration without containing domain knowledge. Each planner
knows how to turn ONE goal type into a task DAG. Adding a new domain/goal is
just registering a planner - never editing the Orchestra core.

A planner has the signature:  plan(intent, make_task) -> list[task]
where make_task is the Orchestra's validated task factory:
  make_task(intent, type, adapter, inputs, side_effect=..., depends=[...],
            requires_approval=bool) -> task
"""

from __future__ import annotations

from typing import Any, Callable

MakeTask = Callable[..., dict[str, Any]]
Planner = Callable[[dict[str, Any], MakeTask], list[dict[str, Any]]]


class PlannerRegistry:
    def __init__(self) -> None:
        self._planners: dict[str, Planner] = {}

    def register(self, goal_type: str, planner: Planner) -> None:
        self._planners[goal_type] = planner

    def get(self, goal_type: str) -> Planner | None:
        return self._planners.get(goal_type)

    def known(self) -> list[str]:
        return sorted(self._planners)


# --- single-task planners (migrated from the old hardcoded if-chain) ---

def plan_watchlist_add(intent: dict[str, Any], mk: MakeTask) -> list[dict[str, Any]]:
    return [mk(intent, "add_to_watchlist", "watchlist",
               intent["goal"].get("params", {}), side_effect="idempotent")]


def plan_open_url(intent: dict[str, Any], mk: MakeTask) -> list[dict[str, Any]]:
    return [mk(intent, "open_url", "droidpuppy",
               intent["goal"].get("params", {}), side_effect="idempotent")]


def plan_launch_app(intent: dict[str, Any], mk: MakeTask) -> list[dict[str, Any]]:
    return [mk(intent, "launch_app", "droidpuppy",
               intent["goal"].get("params", {}), side_effect="idempotent")]


def plan_place_order(intent: dict[str, Any], mk: MakeTask) -> list[dict[str, Any]]:
    return [mk(intent, "place_order", "broker",
               intent["goal"].get("params", {}),
               side_effect="irreversible", requires_approval=True)]


# --- a NEW multi-step planner proving the DAG + dependencies + handoffs ---

def plan_prepare_and_trade(intent: dict[str, Any], mk: MakeTask) -> list[dict[str, Any]]:
    """One intent -> a 3-step pipeline across three adapters:

        1. add the contract to the watchlist        (watchlist, idempotent)
        2. open the cockpit on the device            (droidpuppy, depends on 1)
        3. place the order                           (broker, irreversible,
                                                      requires approval, depends on 2)

    This exercises multi-adapter routing, dependency ordering, and the approval
    gate landing on the final irreversible step - all from a single goal.
    """
    p = intent["goal"].get("params", {})
    t_watch = mk(intent, "add_to_watchlist", "watchlist",
                 p.get("contract", {}), side_effect="idempotent")
    t_open = mk(intent, "open_url", "droidpuppy",
                {"url": p.get("cockpit_url", "https://example.com"),
                 "browser": "com.brave.browser"},
                side_effect="idempotent", depends=[t_watch["task_id"]])
    t_order = mk(intent, "place_order", "broker", p.get("order", {}),
                 side_effect="irreversible", requires_approval=True,
                 depends=[t_open["task_id"]])
    return [t_watch, t_open, t_order]


def default_registry() -> PlannerRegistry:
    reg = PlannerRegistry()
    reg.register("watchlist_add", plan_watchlist_add)
    reg.register("open_url", plan_open_url)
    reg.register("launch_app", plan_launch_app)
    reg.register("place_order", plan_place_order)
    reg.register("prepare_and_trade", plan_prepare_and_trade)
    return reg
