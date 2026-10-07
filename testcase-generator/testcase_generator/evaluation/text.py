"""Text helpers shared by the rule-based metrics."""

from __future__ import annotations

import re
from typing import Any


def normalize_text(text: str) -> str:
    """Lowercase, unify quotes and reduce everything else to single-spaced words."""
    text = (text or "").lower()
    text = text.replace("„", '"').replace("“", '"').replace("’", "'")
    text = re.sub(r"[^a-z0-9äöüß/\-\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def case_text(test_case: dict[str, Any]) -> str:
    """Normalized title, type, steps and expected results of one test case."""
    parts = [str(test_case.get("title", "")), str(test_case.get("type", ""))]
    for key in ("navigation_steps", "steps_only", "steps"):
        for step in test_case.get(key, []) or []:
            if isinstance(step, dict):
                parts.append(str(step.get("step", "")))
                parts.append(str(step.get("expected", "")))
            else:
                parts.append(str(step))
    return normalize_text(" ".join(parts))


def acceptance_criteria_lines(ac_blob: str) -> list[str]:
    return [line.strip() for line in ac_blob.splitlines() if line.strip()]
