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

"""Server-side A2UI (Agent-to-UI) support for GEAP agents.

See docs/A2UI.md for the full architecture writeup. In short: agents that
want to hand the client a rich, structured UI (instead of only prose) build
an envelope with :mod:`app.a2ui.envelope`, validate it with
:mod:`app.a2ui.validate`, and return it from a ``FunctionTool``. The
component vocabulary both sides agree on lives in :mod:`app.a2ui.catalog`.
"""

from app.a2ui.catalog import CATALOG_ID, CATALOG_VERSION, COMPONENT_TYPES
from app.a2ui.envelope import SurfaceBuilder
from app.a2ui.planning_envelope import (
    PlanningA2uiValidationError,
    build_planning_envelope,
    default_planning_envelope,
    validate_planning_envelope,
)
from app.a2ui.validate import A2uiValidationError, validate_envelope

__all__ = [
    "CATALOG_ID",
    "CATALOG_VERSION",
    "COMPONENT_TYPES",
    "A2uiValidationError",
    "PlanningA2uiValidationError",
    "SurfaceBuilder",
    "build_planning_envelope",
    "default_planning_envelope",
    "validate_envelope",
    "validate_planning_envelope",
]
