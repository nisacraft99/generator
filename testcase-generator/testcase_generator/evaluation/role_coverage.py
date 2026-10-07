"""Role Coverage: are all roles named in the user story used in a login step?

A role counts as required when the story or its acceptance criteria name it as
an actor or in a permission rule. It counts as covered when at least one
generated step explicitly logs in with that role.
"""

from __future__ import annotations

import re
from typing import Any

from ..config import ROLES
from .text import normalize_text


def required_roles(story: str, ac_blob: str) -> list[str]:
    """Roles named as actor or in a permission rule.

    Module names such as "Strategic Meeting" or "Team Meeting" do not match,
    because every pattern requires actor or permission wording around the role.
    """
    text = normalize_text(story + " " + ac_blob)
    found = set()
    for role in ROLES:
        patterns = [
            rf"\bas\s+(?:a|an)?\s*{role}\b",
            rf"\buser\s+with\s+the\s+role\s+{role}\b",
            rf"\b{role}\s+can\b",
            rf"\b{role}s\s+can\b",
            rf"\b{role}\s+cannot\b",
            rf"\b{role}s\s+cannot\b",
            rf"\b{role}\s+can\s+not\b",
            rf"\b{role}s\s+can\s+not\b",
            rf"\bonly\s+(?:a\s+|an\s+)?(?:user\s+with\s+the\s+role\s+)?{role}\b",
            rf"\blogged\s+in\s+{role}\b",
        ]
        if any(re.search(pattern, text) for pattern in patterns):
            found.add(role)
    return sorted(found)


def step_logs_in_as(step_text: str, role: str) -> bool:
    """True if this single step logs in with ``role``.

    Wording between the login phrase and the role is allowed ("Log in as the
    assigned Agent"), but it may not cross another role name first. "Log in as
    Manager and review data for Agent" therefore counts for Manager only.
    """
    text = normalize_text(step_text)
    if not text:
        return False

    any_role = "|".join(re.escape(name) for name in ROLES)
    pattern = re.compile(
        rf"\b(?:log\s*in|login|logged\s*in|sign\s*in|signed\s*in)\s+"
        rf"(?:as|with)\s+"
        rf"(?:(?!\b(?:{any_role})\b).)*?"
        rf"\b{re.escape(role.lower())}\b",
        flags=re.IGNORECASE,
    )
    return bool(pattern.search(text))


def generated_roles(cases: list[dict[str, Any]]) -> list[str]:
    """Roles used in a login step. Only the action text of each step is inspected."""
    found = set()
    for case in cases:
        for step in case.get("steps", []) or []:
            if not isinstance(step, dict):
                continue
            step_text = str(step.get("step", ""))
            for role in ROLES:
                if step_logs_in_as(step_text, role):
                    found.add(role)
    return sorted(found)


def evaluate_role_coverage(story: str, ac_blob: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    required = required_roles(story, ac_blob)
    generated = generated_roles(cases)
    covered = sorted(set(required) & set(generated))
    missing = sorted(set(required) - set(generated))

    return {
        "overall_pct": round(len(covered) / len(required) * 100, 2) if required else None,
        "covered_count": len(covered),
        "total_count": len(required),
        "required_roles": required,
        "generated_roles": generated,
        "missing_roles": missing,
    }
