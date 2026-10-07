"""Shared resources of generation and evaluation: API client, UI context, navigation targets."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from . import config
from .ui_model import UiContext

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


@dataclass(frozen=True)
class Resources:
    """Everything generation and evaluation need besides the user story itself."""

    client: Any
    ui_context: UiContext
    navigation_targets: dict[str, Any]


def load_json(path: Path, default: Any) -> Any:
    """Return the parsed JSON file, or ``default`` if it is missing or invalid."""
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def digest(content: Any) -> str:
    """SHA-256 of a text or of a JSON-serialisable object, to record which inputs a run used."""
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def create_client() -> Any:
    """Create the OpenAI client from OPENAI_API_KEY, or return None if unavailable."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return None
    return OpenAI(api_key=api_key)


def load_resources() -> Resources:
    targets = load_json(config.NAVIGATION_TARGETS_PATH, {})
    return Resources(
        client=create_client(),
        ui_context=UiContext(load_json(config.UI_CONTEXT_PATH, {})),
        navigation_targets=targets if isinstance(targets, dict) else {},
    )
