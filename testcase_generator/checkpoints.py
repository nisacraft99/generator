"""Checkpoint files of a bulk run.

A checkpoint stores the settings of the experiment and, per run, the generated
test cases with a record of the model call, every judge decision and the
computed metrics. It is written after each generation and each judge
call, so an interrupted bulk run continues without repeating paid API calls.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
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


# Settings that shape what the generator produces. If one of them changes, saved
# generations no longer belong to the experiment and a new checkpoint is started.
GENERATION_SETTINGS = (
    "generator_model",
    "generator_reasoning_effort",
    "generator_temperature",
    "generator_prompt_sha256",
    "ui_context_sha256",
)


def fingerprint(stories: list[dict[str, Any]], repetitions: int, settings: dict[str, Any]) -> str:
    """Identify a bulk run by its user stories, repetition count and generation settings.

    The same inputs resume the same checkpoint. Settings that only affect the
    evaluation (judge, navigation targets) are not part of the fingerprint: the
    saved generations stay valid and are simply evaluated again.
    """
    return _digest(
        {
            "version": config.CHECKPOINT_VERSION,
            "repetitions": int(repetitions),
            "userstories": stories,
            "generation": {name: settings.get(name) for name in GENERATION_SETTINGS},
        }
    )


def path_for(stories: list[dict[str, Any]], repetitions: int, settings: dict[str, Any]) -> Path:
    return config.CHECKPOINT_DIR / f"bulk_{fingerprint(stories, repetitions, settings)}.json"


def path_for_upload(checkpoint: dict[str, Any]) -> Path:
    """Local working copy of an uploaded checkpoint, so re-evaluation can be resumed too."""
    return config.CHECKPOINT_DIR / f"uploaded_{_digest(checkpoint)}.json"


def new(stories: list[dict[str, Any]], repetitions: int, settings: dict[str, Any]) -> dict[str, Any]:
    return {
        "checkpoint_version": config.CHECKPOINT_VERSION,
        "fingerprint": fingerprint(stories, repetitions, settings),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "settings": settings,
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
    """Write atomically, so a crash cannot leave a half-written checkpoint.

    Every write goes to a temporary file of its own. Two sessions of the app
    that save the same checkpoint at the same moment therefore cannot take
    each other's temporary file away.
    """
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=directory, prefix=f"{os.path.basename(path)}.", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(checkpoint, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(temporary)
        raise


def saved_bulk_runs() -> list[dict[str, Any]]:
    """Summaries of the bulk checkpoints on disk, newest first."""
    found = []
    for path in config.CHECKPOINT_DIR.glob("bulk_*.json"):
        checkpoint = load(path)
        if checkpoint is None:
            continue
        found.append(
            {
                "path": path,
                "repetitions": checkpoint.get("repetitions"),
                "total_runs": checkpoint.get("total_runs"),
                "created_at": str(checkpoint.get("created_at", "")),
                "generator_model": (checkpoint.get("settings") or {}).get("generator_model"),
                **stats(checkpoint),
            }
        )
    return sorted(found, key=lambda entry: entry["created_at"], reverse=True)


def restore(uploaded: dict[str, Any]) -> Path:
    """Put an uploaded bulk checkpoint back on disk, so that its run can be resumed.

    A checkpoint already on disk is kept if it has at least as much progress.
    """
    fingerprint_value = uploaded.get("fingerprint")
    if uploaded.get("checkpoint_version") != config.CHECKPOINT_VERSION or not (
        isinstance(fingerprint_value, str) and re.fullmatch(r"[0-9a-f]{20}", fingerprint_value)
    ):
        raise ValueError("This file is not a bulk checkpoint of this app and cannot be resumed.")
    path = config.CHECKPOINT_DIR / f"bulk_{fingerprint_value}.json"
    existing = load(path)
    if existing is not None:
        old, new_stats = stats(existing), stats(uploaded)
        if old["completed"] >= new_stats["completed"] and old["generated"] >= new_stats["generated"]:
            return path
    save(path, uploaded)
    return path


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
