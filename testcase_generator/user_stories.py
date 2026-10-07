"""Loading and lookup of the user stories."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def load_user_stories(source: Any) -> list[dict[str, Any]]:
    """Load and validate user stories from a file path or an open JSON file.

    Expected format: a list of objects with ``id``, ``title``, ``story`` and a
    non-empty list ``acceptance_criteria``. Each story is returned with its
    criteria joined into ``ac_blob`` (one criterion per line).
    """
    try:
        if isinstance(source, (str, Path)):
            with open(source, encoding="utf-8") as handle:
                data = json.load(handle)
        else:
            data = json.load(source)
    except Exception as error:
        raise ValueError(f"Could not read bulk user stories JSON: {error}") from error

    if not isinstance(data, list):
        raise ValueError("Bulk user stories JSON must contain a list of user stories.")

    stories = []
    for index, entry in enumerate(data, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry {index} is not a JSON object.")

        story_id = str(entry.get("id", "")).strip()
        story = str(entry.get("story", "")).strip()
        criteria = entry.get("acceptance_criteria", [])

        if not story_id:
            raise ValueError(f"Entry {index} is missing 'id'.")
        if not story:
            raise ValueError(f"Entry {index} is missing 'story'.")
        if not isinstance(criteria, list) or not criteria:
            raise ValueError(f"Entry {index} must contain a non-empty list 'acceptance_criteria'.")

        lines = [str(criterion).strip() for criterion in criteria if str(criterion).strip()]
        if not lines:
            raise ValueError(f"Entry {index} has no usable acceptance criteria.")

        stories.append(
            {
                "id": story_id,
                "title": str(entry.get("title", "")).strip(),
                "story": story,
                "ac_blob": "\n".join(lines),
                "acceptance_criteria_count": len(lines),
            }
        )
    return stories


def normalize_story_id(value: Any) -> str:
    """Turn inputs such as ``1``, ``01`` or ``us-1`` into ``US-1``."""
    raw = str(value or "").strip().upper()
    if not raw:
        return ""
    match = re.search(r"(\d+)", raw)
    return f"US-{int(match.group(1))}" if match else raw


def find_user_story(stories: list[dict[str, Any]], lookup: Any) -> dict[str, Any] | None:
    wanted = normalize_story_id(lookup)
    for story in stories:
        if normalize_story_id(story.get("id", "")) == wanted:
            return story
    return None
