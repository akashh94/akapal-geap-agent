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

"""Mock retirement-planning data and the A2UI dashboard tool.

Figures are fixed demo constants (no live account/market integration exists
yet), kept intentionally identical to the numbers ``planning.js`` and
``chat.js`` already showed on the client before this rewrite, so the
before/after behavior matches for the same mock user.
"""

import logging

from app.a2ui.planning_envelope import (
    build_planning_envelope,
    default_planning_envelope,
)

_logger = logging.getLogger(__name__)

_TARGET_AGE = 65
_TARGET_YEAR = 2046
_CURRENT_SAVINGS = 84230.15
_PROJECTED_VALUE_AT_TARGET_AGE = 1_245_000
_SUCCESS_PROBABILITY_PCT = 84
_DEFAULT_SIMULATIONS = 1000
_CURRENT_AGE = 47

_GLIDE_PATH_ALLOCATION = [
    {"label": "U.S. Equities", "weight_pct": 45, "value": 37903.57},
    {"label": "Intl Equities", "weight_pct": 20, "value": 16846.03},
    {"label": "Fixed Income", "weight_pct": 25, "value": 21057.54},
    {"label": "Cash & Savings", "weight_pct": 10, "value": 8423.01},
]

# Mock target-date glide path: equity weight steps down (and bond weight
# steps up) every five years as the mock user approaches _TARGET_AGE.
_GLIDE_PATH_SERIES = [
    {"age": 45, "equity_pct": 65, "bond_pct": 35},
    {"age": 50, "equity_pct": 58, "bond_pct": 42},
    {"age": 55, "equity_pct": 51, "bond_pct": 49},
    {"age": 60, "equity_pct": 45, "bond_pct": 55},
    {"age": _TARGET_AGE, "equity_pct": 40, "bond_pct": 60},
]


def get_retirement_summary() -> dict:
    """Return the mock user's retirement target age/year and savings progress."""
    return {
        "target_age": _TARGET_AGE,
        "target_year": _TARGET_YEAR,
        "current_savings": _CURRENT_SAVINGS,
        "projected_value_at_target_age": _PROJECTED_VALUE_AT_TARGET_AGE,
    }


def run_monte_carlo_projection(simulations: int = _DEFAULT_SIMULATIONS) -> dict:
    """Run mock Monte Carlo retirement projections and return a success probability.

    Args:
        simulations: number of distinct market permutations to simulate.
    """
    return {
        "simulations": simulations,
        "success_probability_pct": _SUCCESS_PROBABILITY_PCT,
        "risk_rating": "High" if _SUCCESS_PROBABILITY_PCT >= 75 else "Elevated",
    }


def get_glide_path_allocation() -> list[dict]:
    """Return the mock target-date glide path's current asset allocation mix."""
    return [dict(row) for row in _GLIDE_PATH_ALLOCATION]


def _build_monte_carlo_series(summary: dict, projection: dict) -> dict:
    """Derive mock p10/p50/p90 percentile bands from current savings to the
    projected value at the target age, spread by the success probability."""
    years = max(summary["target_age"] - _CURRENT_AGE, 1)
    spread_factor = (1 - projection["success_probability_pct"] / 100) * 0.6
    p10, p50, p90 = [], [], []
    for year in range(years + 1):
        age = _CURRENT_AGE + year
        fraction = year / years
        midpoint = summary["current_savings"] + fraction * (
            summary["projected_value_at_target_age"] - summary["current_savings"]
        )
        spread = midpoint * spread_factor
        p10.append({"age": age, "value": round(midpoint - spread, 2)})
        p50.append({"age": age, "value": round(midpoint, 2)})
        p90.append({"age": age, "value": round(midpoint + spread, 2)})
    return {"p10": p10, "p50": p50, "p90": p90}


def render_retirement_dashboard() -> dict:
    """Signal the client to render the retirement health-check A2UI charts.

    Call this once, after you've discussed the retirement health check
    results in your normal text reply, so the client renders the
    interactive glide-path/Monte Carlo/allocation charts alongside your
    explanation. Takes no arguments -- it pulls the same figures your other
    retirement tool calls already returned, so the charts can never show
    different numbers than your prose does.

    Always returns a valid ``a2ui`` envelope, even if the underlying figures
    can't be composed for any reason -- retirement health-check responses
    must never omit the chart payload.
    """
    try:
        summary = get_retirement_summary()
        projection = run_monte_carlo_projection()
        allocation = get_glide_path_allocation()

        envelope = build_planning_envelope(
            glide_path_series=[dict(point) for point in _GLIDE_PATH_SERIES],
            monte_carlo_series=_build_monte_carlo_series(summary, projection),
            monte_carlo_target=summary["projected_value_at_target_age"],
            allocation_segments=[
                {"label": row["label"], "weight_pct": row["weight_pct"]}
                for row in allocation
            ],
            success_rate=f"{projection['success_probability_pct']}%",
            target_age=summary["target_age"],
            current_savings=f"${summary['current_savings']:,.2f}",
            target_portfolio=f"${summary['projected_value_at_target_age']:,.0f}",
        )
    except Exception:
        # Failsafe: a retirement health-check response must never omit a2ui,
        # even if composing real chart data fails for any reason. Log so
        # regressions in chart composition stay observable.
        _logger.exception(
            "render_retirement_dashboard: falling back to default A2UI envelope"
        )
        envelope = default_planning_envelope()

    return {"a2ui": envelope}
