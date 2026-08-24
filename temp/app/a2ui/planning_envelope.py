# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Strict A2UI envelope contract for retirement health-check chat responses.

This is deliberately a *different*, smaller envelope shape than
:class:`app.a2ui.envelope.SurfaceBuilder`'s flat ``createSurface`` /
``updateComponents`` / ``updateDataModel`` message list (used for the
standalone planning dashboard page). The chat UI mounts A2UI with
``<a2ui-view data-root="charts" ...>``, which expects a small nested tree:
one ``root`` surface whose ``children.charts`` is a ``chart_tabs`` component
with exactly three chart children (``glide_path``, ``monte_carlo``,
``allocation``), plus an ``updateDataModel.planning`` block of summary
metrics. Narrative explanation stays in the agent's prose response; only
numeric/structured chart data belongs here.

For retirement-planning intents this envelope must never be omitted or
``null``. If real chart data can't be composed, callers should fall back to
:func:`default_planning_envelope`, a canonical, valid, conservative-default
copy of this same contract.
"""

from __future__ import annotations

import copy

from app.a2ui.catalog import COMPONENT_TYPES

PLANNING_A2UI_VERSION = "1.0"

_REQUIRED_CHART_CHILDREN = ("glide_path", "monte_carlo", "allocation")


class PlanningA2uiValidationError(ValueError):
    """Raised when a retirement charts A2UI envelope violates the strict contract."""


# Canonical failsafe template: always valid, always satisfies the contract.
# Deep-copy via default_planning_envelope() before mutating/returning it.
DEFAULT_PLANNING_A2UI: dict = {
    "version": PLANNING_A2UI_VERSION,
    "root": {
        "type": "surface",
        "props": {"title": "Planning & Retirement"},
        "children": {
            "charts": {
                "type": "chart_tabs",
                "props": {"defaultTab": "glide_path"},
                "children": {
                    "glide_path": {
                        "type": "glide_path_chart",
                        "props": {"series": []},
                    },
                    "monte_carlo": {
                        "type": "monte_carlo_chart",
                        "props": {
                            "series": {"p10": [], "p50": [], "p90": []},
                            "target": 0,
                        },
                    },
                    "allocation": {
                        "type": "allocation_chart",
                        "props": {"segments": []},
                    },
                },
            },
        },
    },
    "updateDataModel": {
        "planning": {
            "successRate": "",
            "targetAge": 0,
            "currentSavings": "",
            "targetPortfolio": "",
        },
    },
}


def default_planning_envelope() -> dict:
    """Return a fresh, independent copy of the canonical failsafe envelope."""
    return copy.deepcopy(DEFAULT_PLANNING_A2UI)


def build_planning_envelope(
    *,
    glide_path_series: list,
    monte_carlo_series: dict,
    monte_carlo_target,
    allocation_segments: list,
    success_rate: str,
    target_age: int,
    current_savings: str,
    target_portfolio: str,
) -> dict:
    """Build the strict retirement health-check charts A2UI envelope.

    All chart data must already be plain numeric/structured values (no
    markdown/prose) -- this function does not sanitize its inputs. Raises
    :class:`PlanningA2uiValidationError` (via :func:`validate_planning_envelope`)
    if the assembled envelope doesn't satisfy the contract; callers should
    catch that and fall back to :func:`default_planning_envelope`.
    """
    envelope = {
        "version": PLANNING_A2UI_VERSION,
        "root": {
            "type": "surface",
            "props": {"title": "Planning & Retirement"},
            "children": {
                "charts": {
                    "type": "chart_tabs",
                    "props": {"defaultTab": "glide_path"},
                    "children": {
                        "glide_path": {
                            "type": "glide_path_chart",
                            "props": {"series": glide_path_series},
                        },
                        "monte_carlo": {
                            "type": "monte_carlo_chart",
                            "props": {
                                "series": monte_carlo_series,
                                "target": monte_carlo_target,
                            },
                        },
                        "allocation": {
                            "type": "allocation_chart",
                            "props": {"segments": allocation_segments},
                        },
                    },
                },
            },
        },
        "updateDataModel": {
            "planning": {
                "successRate": success_rate,
                "targetAge": target_age,
                "currentSavings": current_savings,
                "targetPortfolio": target_portfolio,
            },
        },
    }
    validate_planning_envelope(envelope)
    return envelope


def validate_planning_envelope(payload: dict) -> None:
    """Raise :class:`PlanningA2uiValidationError` unless ``payload`` satisfies
    the strict retirement health-check A2UI contract:

    - ``version == "1.0"``
    - ``root.type == "surface"``
    - ``root.children.charts`` exists and ``charts.type == "chart_tabs"``
    - ``charts.children`` includes ``glide_path``, ``monte_carlo``, ``allocation``
    - ``updateDataModel.planning`` contains the summary metric keys

    Returns ``None`` on success.
    """
    if not isinstance(payload, dict):
        raise PlanningA2uiValidationError(
            f"a2ui payload must be a dict, got {type(payload).__name__}"
        )

    if payload.get("version") != PLANNING_A2UI_VERSION:
        raise PlanningA2uiValidationError(
            f"a2ui.version must be {PLANNING_A2UI_VERSION!r}, got {payload.get('version')!r}"
        )

    root = payload.get("root")
    if not isinstance(root, dict) or root.get("type") != "surface":
        raise PlanningA2uiValidationError("a2ui.root.type must be 'surface'")

    charts = (
        root.get("children", {}).get("charts")
        if isinstance(root.get("children"), dict)
        else None
    )
    if not isinstance(charts, dict):
        raise PlanningA2uiValidationError("a2ui.root.children.charts must exist")
    if charts.get("type") != "chart_tabs":
        raise PlanningA2uiValidationError(
            "a2ui.root.children.charts.type must be 'chart_tabs'"
        )

    chart_children = charts.get("children")
    if not isinstance(chart_children, dict):
        raise PlanningA2uiValidationError("a2ui charts.children must be an object")
    for child_id in _REQUIRED_CHART_CHILDREN:
        child = chart_children.get(child_id)
        if not isinstance(child, dict):
            raise PlanningA2uiValidationError(
                f"a2ui charts.children is missing required entry {child_id!r}"
            )
        if child.get("type") not in COMPONENT_TYPES:
            known = ", ".join(sorted(COMPONENT_TYPES))
            raise PlanningA2uiValidationError(
                f"a2ui charts.children[{child_id!r}] has unknown type "
                f"{child.get('type')!r}. Known types: {known}"
            )

    data_model = payload.get("updateDataModel")
    planning_data = data_model.get("planning") if isinstance(data_model, dict) else None
    if not isinstance(planning_data, dict):
        raise PlanningA2uiValidationError("a2ui.updateDataModel.planning must exist")
    for key in ("successRate", "targetAge", "currentSavings", "targetPortfolio"):
        if key not in planning_data:
            raise PlanningA2uiValidationError(
                f"a2ui.updateDataModel.planning is missing required key {key!r}"
            )
