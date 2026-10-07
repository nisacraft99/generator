"""Checkpoint files of a bulk run.

A checkpoint stores, per run, the generated test cases, every judge decision
and the computed metrics. It is written after each generation and each judge
call, so an interrupted bulk run continues without repeating paid API calls.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from . import config


def run_key(story_id: str, variant: str, repetition: int) -> str:
    return f"{story_id}|{variant}|rep{repetition}"


def new_run_state(story: dict[str, Any], variant: str, repetition: int, use_ui_context: bool) -> dict[str, Any]:
    return {
        "item": story,
        "variant": variant,
        "rep": repetition,
        "use_ui_context": use_ui_context,
        "generation_complete": False,
        "complete": False,
        "cases": [],
        "open_q": [],
        "ac_judge": {"details": {}},
    }


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def fingerprint(stories: list[dict[str, Any]], repetitions: int) -> str:
    """Identify a bulk run by its user stories, repetition count and models.

    The same inputs resume the same checkpoint. The UI context, the navigation
    targets and the prompts are not part of the fingerprint: after changing
    them, clear the checkpoint to generate from scratch.
    """
    return _digest(
        {
            "version": config.CHECKPOINT_VERSION,
            "repetitions": int(repetitions),
            "userstories": stories,
            "generation_model": config.GENERATOR_MODEL,
            "judge_model": config.JUDGE_MODEL,
        }
    )


def path_for(stories: list[dict[str, Any]], repetitions: int) -> Path:
    return config.CHECKPOINT_DIR / f"bulk_{fingerprint(stories, repetitions)}.json"


def path_for_upload(checkpoint: dict[str, Any]) -> Path:
    """Local working copy of an uploaded checkpoint, so re-evaluation can be resumed too."""
    return config.CHECKPOINT_DIR / f"uploaded_{_digest(checkpoint)}.json"


def new(stories: list[dict[str, Any]], repetitions: int) -> dict[str, Any]:
    return {
        "checkpoint_version": config.CHECKPOINT_VERSION,
        "fingerprint": fingerprint(stories, repetitions),
        "repetitions": int(repetitions),
        "total_runs": len(stories) * int(repetitions) * len(config.VARIANTS),
        "runs": {},
    }


def load(path: Path | str | None) -> dict[str, Any] | None:
    """Return the checkpoint at ``path``, or None if it is missing, unreadable or outdated."""
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("checkpoint_version") != config.CHECKPOINT_VERSION:
        return None
    data.setdefault("runs", {})
    return data


def save(path: Path | str, checkpoint: dict[str, Any]) -> None:
    """Write atomically, so a crash cannot leave a half-written checkpoint."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = f"{path}.tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(checkpoint, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def delete(path: Path | str | None) -> None:
    if path and os.path.exists(path):
        os.remove(path)


def stats(checkpoint: dict[str, Any] | None) -> dict[str, int]:
    """Count finished runs, saved generations and judge decisions."""
    runs = checkpoint.get("runs", {}) if isinstance(checkpoint, dict) else {}
    counts = {"completed": 0, "generated": 0, "judge_done": 0, "judge_failed": 0}
    for run in runs.values():
        if not isinstance(run, dict):
            continue
        counts["generated"] += bool(run.get("generation_complete"))
        counts["completed"] += bool(run.get("complete"))
        details = run.get("ac_judge", {}).get("details", {})
        if isinstance(details, dict):
            for judgement in details.values():
                if isinstance(judgement, dict):
                    counts["judge_done"] += judgement.get("status") == "complete"
                    counts["judge_failed"] += judgement.get("status") == "failed"
    return counts


def read_upload(uploaded_file: Any) -> dict[str, Any]:
    """Read and validate a checkpoint uploaded in the UI.

    Accepts a checkpoint backup (an object with a top-level ``runs`` entry) or a
    plain ``{run key: run}`` object.
    """
    if uploaded_file is None:
        raise ValueError("No checkpoint file uploaded.")
    with contextlib.suppress(Exception):
        uploaded_file.seek(0)

    try:
        raw = uploaded_file.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
    except Exception as error:
        raise ValueError(f"Could not read checkpoint JSON: {error}") from error

    if isinstance(data, dict) and isinstance(data.get("runs"), dict):
        checkpoint = data
    elif isinstance(data, dict) and data and all(isinstance(value, dict) for value in data.values()):
        if not any("cases" in value or "generation_complete" in value for value in data.values()):
            raise ValueError("JSON is not a recognizable bulk checkpoint/run file.")
        checkpoint = {
            "checkpoint_version": config.CHECKPOINT_VERSION,
            "fingerprint": "uploaded-runs",
            "repetitions": None,
            "total_runs": len(data),
            "runs": data,
        }
    else:
        raise ValueError("Expected a bulk checkpoint JSON containing a top-level 'runs' object.")

    checkpoint.setdefault("checkpoint_version", config.CHECKPOINT_VERSION)
    if checkpoint.get("checkpoint_version") != config.CHECKPOINT_VERSION:
        raise ValueError(
            f"Unsupported checkpoint version: {checkpoint.get('checkpoint_version')} "
            f"(expected {config.CHECKPOINT_VERSION})."
        )
    checkpoint.setdefault("runs", {})
    if not checkpoint["runs"]:
        raise ValueError("Checkpoint contains no runs.")
    return checkpoint


def run_identity(key: str, run: dict[str, Any]) -> tuple[str, str, int]:
    """Story ID, variant and repetition of a saved run, falling back to its key."""
    story_id = str((run.get("item") or {}).get("id", "")).strip()
    variant = str(run.get("variant", "")).strip()
    repetition = run.get("rep")

    parts = str(key).split("|")
    if not story_id and parts:
        story_id = parts[0]
    if not variant and len(parts) >= 2:
        variant = parts[1]
    if repetition in (None, "") and len(parts) >= 3:
        match = re.search(r"(\d+)", parts[2])
        if match:
            repetition = int(match.group(1))

    try:
        repetition = int(repetition)
    except (TypeError, ValueError):
        repetition = 0
    return story_id, variant, repetition
