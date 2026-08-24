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

"""Deterministic retirement health-check intent matching.

The strict A2UI chart contract (see ``app.a2ui.planning_envelope``) only
applies to retirement-planning health-check intents -- it must not be forced
onto unrelated planning questions. Matching happens on normalized text:

1. lowercase
2. collapse whitespace (``\\s+`` -> single space)
3. trim

so that phrasing/spacing/case variants of the same request (e.g. "Run
retirement planning health check.", "retirement health check diagnostic")
all match consistently.
"""

from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"\s+")

# Keyword phrases that identify a retirement health-check style request.
# Matched against normalized text as substrings, so word order/punctuation
# around them doesn't matter.
_RETIREMENT_HEALTH_CHECK_PHRASES = (
    "retirement health check",
    "retirement planning health check",
    "retirement diagnostic",
    "retirement check up",
    "retirement checkup",
)


def normalize_intent_text(text: str) -> str:
    """Lowercase, collapse internal whitespace, and trim ``text``."""
    return _WHITESPACE_RE.sub(" ", text.lower()).strip()


def is_retirement_health_check_intent(text: str) -> bool:
    """Return whether normalized ``text`` matches a retirement health-check intent.

    Matches phrases such as "Run retirement planning health check.",
    "retirement planning health check", and "retirement health check
    diagnostic" regardless of case, punctuation, or extra whitespace.
    """
    normalized = normalize_intent_text(text)
    if not normalized:
        return False
    if any(phrase in normalized for phrase in _RETIREMENT_HEALTH_CHECK_PHRASES):
        return True
    return "retirement" in normalized and (
        "health check" in normalized or "diagnostic" in normalized
    )
