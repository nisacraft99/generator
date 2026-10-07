"""Test case generation with the LLM and parsing of its JSON answer."""

from __future__ import annotations

import ast
import json
import re
from typing import Any

from . import config
from .resources import load_prompt

# Technical failures are reported through the open-questions list. The bulk run
# recognises them by these texts and never scores them as test quality.
CLIENT_MISSING = "OpenAI client not initialized (missing OPENAI_API_KEY or openai package)."
INVALID_JSON = "Model response was not valid JSON."
CALL_FAILED_PREFIX = "OpenAI call failed:"


def _first_json_object(text: str) -> str | None:
    """Return the first balanced ``{...}`` block, ignoring braces inside strings."""
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def parse_model_json(text: str) -> dict[str, Any]:
    """Parse the model answer, repairing common formatting slips locally.

    Tried in order: strict JSON, JSON without trailing commas, and a Python
    literal (single quotes, True/None). Code fences and text around the JSON
    object are ignored. If nothing parses, the result carries INVALID_JSON.
    """
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S | re.I).strip()

    candidates = [text]
    balanced = _first_json_object(text)
    if balanced and balanced != text:
        candidates.append(balanced)

    for candidate in candidates:
        without_trailing_commas = re.sub(r",\s*([}\]])", r"\1", candidate)
        for parse, source in (
            (json.loads, candidate),
            (json.loads, without_trailing_commas),
            (ast.literal_eval, candidate),
        ):
            try:
                data = parse(source)
            except Exception:
                continue
            if isinstance(data, dict):
                return data

    return {"test_cases": [], "open_questions": [INVALID_JSON]}


def _normalize_step(step: Any) -> dict[str, Any]:
    if isinstance(step, dict):
        return {
            "step": (step.get("step", "") or "").strip(),
            "expected": (step.get("expected", "") or "").strip(),
            "ui_node_id": step.get("ui_node_id", None),
        }
    return {"step": str(step), "expected": "", "ui_node_id": None}


def _is_blank(step: dict[str, Any]) -> bool:
    return (step.get("step") or "").strip() in {"", "—"} and (step.get("expected") or "").strip() in {"", "—"}


def _normalize_test_case(raw: dict[str, Any]) -> dict[str, Any]:
    """Bring a test case into the internal shape.

    ``steps`` holds navigation steps followed by test steps, as shown to the
    tester and the judge; the two original lists are kept alongside it.
    """
    navigation_steps = [_normalize_step(step) for step in (raw.get("navigation_steps", []) or [])]
    test_steps = [_normalize_step(step) for step in (raw.get("steps", []) or [])]
    return {
        "id": (raw.get("id", "") or "").strip(),
        "title": (raw.get("title", "") or "").strip(),
        "priority": (raw.get("priority", "") or "").strip(),
        "type": (raw.get("type", "") or "").strip(),
        "navigation_steps": navigation_steps,
        "steps_only": test_steps,
        "steps": [step for step in navigation_steps + test_steps if not _is_blank(step)],
    }


def clean_open_questions(open_questions: list[Any]) -> list[str]:
    """Render every open question as text; the model sometimes returns objects."""
    cleaned = []
    for question in open_questions:
        if isinstance(question, str):
            cleaned.append(question)
        elif question is None:
            cleaned.append("Unspecified open question.")
        else:
            cleaned.append(json.dumps(question, ensure_ascii=False))
    return cleaned


def generate_test_cases(
    client: Any,
    story: str,
    ac_blob: str,
    ui_context: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Generate test cases for one user story. Returns (test cases, open questions).

    Both variants use the same system prompt. Passing ``ui_context`` adds the UI
    description to the model input; that is the only difference between them.
    """
    if not client:
        return [], [CLIENT_MISSING]
    if not story.strip():
        return [], ["User story is empty."]

    payload: dict[str, Any] = {
        "story": story.strip(),
        "acceptance_criteria": [line.strip() for line in ac_blob.splitlines() if line.strip()],
    }
    if ui_context is not None:
        payload["ui_context"] = ui_context

    try:
        response = client.chat.completions.create(
            model=config.GENERATOR_MODEL,
            reasoning_effort=config.GENERATOR_REASONING_EFFORT,
            temperature=config.GENERATOR_TEMPERATURE,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": load_prompt(config.GENERATOR_PROMPT_PATH)},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        )
        data = parse_model_json(response.choices[0].message.content)
        cases = [_normalize_test_case(raw) for raw in (data.get("test_cases", []) or [])]
        return cases, clean_open_questions(data.get("open_questions", []) or [])
    except Exception as error:
        return [], [f"{CALL_FAILED_PREFIX} {error}"]


def generation_failure(open_questions: list[Any]) -> str:
    """Return the technical failure reported by a generation, or an empty string.

    An empty but valid test case list is a model output, not a technical failure.
    """
    for note in (str(question).strip() for question in (open_questions or [])):
        lowered = note.lower()
        if lowered.startswith(CALL_FAILED_PREFIX.lower()):
            return note
        if INVALID_JSON.lower() in lowered:
            return INVALID_JSON
        if "openai client not initialized" in lowered:
            return note
    return ""
