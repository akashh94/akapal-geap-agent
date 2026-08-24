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

"""Validates A2UI envelopes before they ever reach a FunctionTool's return
value, so a malformed payload fails loudly server-side (as a tool error the
agent can react to) instead of silently breaking the renderer in the
browser.

Two passes: a structural JSON Schema pass (message shape), then a semantic
pass in plain Python (component types are known, ``children`` references
resolve, ids are unique) -- a full recursive schema for the polymorphic
component list would be harder to read than the checks it replaces.
"""

from __future__ import annotations

import jsonschema

from app.a2ui.catalog import COMPONENT_TYPES

_ENVELOPE_SCHEMA = {
    "type": "object",
    "required": ["version", "catalogId", "messages"],
    "properties": {
        "version": {"type": "string"},
        "catalogId": {"type": "string"},
        "messages": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["type", "surfaceId"],
                "properties": {
                    "type": {
                        "enum": [
                            "createSurface",
                            "updateComponents",
                            "updateDataModel",
                            "deleteSurface",
                        ]
                    },
                    "surfaceId": {"type": "string", "minLength": 1},
                },
            },
        },
    },
}


class A2uiValidationError(ValueError):
    """Raised for any structural or semantic A2UI envelope defect."""


def validate_envelope(payload: dict) -> None:
    """Raise :class:`A2uiValidationError` if ``payload`` is not a valid
    A2UI envelope for the GEAP planning catalog. Returns ``None`` on success.
    """
    try:
        jsonschema.validate(payload, _ENVELOPE_SCHEMA)
    except jsonschema.ValidationError as exc:
        raise A2uiValidationError(
            f"A2UI envelope failed schema check: {exc.message}"
        ) from exc

    surface_ids = {msg["surfaceId"] for msg in payload["messages"]}
    if len(surface_ids) != 1:
        raise A2uiValidationError(
            f"A2UI envelope must describe exactly one surface, got: {sorted(surface_ids)}"
        )

    for message in payload["messages"]:
        if message["type"] != "updateComponents":
            continue
        components = message.get("components")
        if not isinstance(components, list) or not components:
            raise A2uiValidationError("updateComponents message has no components")

        seen_ids: set[str] = set()
        for component in components:
            for key in ("id", "type"):
                if key not in component:
                    raise A2uiValidationError(
                        f"component missing required key {key!r}: {component!r}"
                    )
            component_id = component["id"]
            component_type = component["type"]
            if component_id in seen_ids:
                raise A2uiValidationError(f"duplicate component id {component_id!r}")
            seen_ids.add(component_id)
            if component_type not in COMPONENT_TYPES:
                known = ", ".join(sorted(COMPONENT_TYPES))
                raise A2uiValidationError(
                    f"component {component_id!r} has unknown type {component_type!r}. "
                    f"Known types: {known}"
                )

        for component in components:
            for child_id in component.get("children", []):
                if child_id not in seen_ids:
                    raise A2uiValidationError(
                        f"component {component['id']!r} references unknown child {child_id!r}"
                    )

        if "root" not in seen_ids:
            raise A2uiValidationError(
                "updateComponents message has no 'root' component"
            )
