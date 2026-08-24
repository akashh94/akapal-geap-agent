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

"""The GEAP planning A2UI catalog.

An A2UI catalog is the vocabulary of components a client already knows how
to render (its own design system) that an agent is allowed to reference.
This one exists to describe exactly one surface today -- the retirement
planning dashboard -- but is written so a second surface can add its own
component types without touching the first.

Every entry here has a matching case in the renderer at
``geap-poc/public/js/a2ui/a2ui-view.js``. The two files are the two halves
of one contract; see docs/A2UI.md for how they're kept in sync. Component
names and prop keys are intentionally identical to the classes/fields
``planning.js`` already used, so this is a re-expression of that markup as
data, not a new visual design.
"""

CATALOG_ID = "geap.planning.v1"
CATALOG_VERSION = "a2ui/0.9"

# type -> (description, required prop keys). "children" holds component ids,
# not props, and is valid on any type; only the props actually read by the
# renderer are enforced here.
COMPONENT_TYPES: dict[str, dict] = {
    "surface": {
        "description": "Root container for a dashboard-style page section.",
        "props": {"title", "subtitle"},
    },
    "hero_cta": {
        "description": "Purple gradient hero card with a headline, body copy, and one action button.",
        "props": {"eyebrow", "title", "body", "badge", "ctaLabel", "ctaQuery"},
    },
    "stat_grid": {
        "description": "Responsive grid of stat_tile children (mirrors .planning-stats-grid).",
        "props": set(),
    },
    "stat_tile": {
        "description": "One labeled metric tile (mirrors .geap-stat-card).",
        "props": {"label", "value", "sublabel", "tone"},
    },
    "tool_grid": {
        "description": "Responsive grid of tool_card children (mirrors .planning-tools-grid).",
        "props": set(),
    },
    "tool_card": {
        "description": "Small card describing one planning tool/technique.",
        "props": {"icon", "title", "body"},
    },
    "safeguard_panel": {
        "description": "Card listing active AI safeguards, each with a status dot.",
        "props": {"title", "footnote"},
    },
    "safeguard_row": {
        "description": "One safeguard entry (name + description + active/inactive status).",
        "props": {"label", "detail", "active"},
    },
    "chart_tabs": {
        "description": (
            "Tabbed container for the retirement health-check charts "
            "(glide path, Monte Carlo, allocation) shown in chat."
        ),
        "props": {"defaultTab"},
    },
    "glide_path_chart": {
        "description": "Target-date glide path chart: equity/bond mix over time.",
        "props": {"series"},
    },
    "monte_carlo_chart": {
        "description": "Monte Carlo percentile band chart (p10/p50/p90) vs. a target value.",
        "props": {"series", "target"},
    },
    "allocation_chart": {
        "description": "Current asset allocation breakdown chart.",
        "props": {"segments"},
    },
}
