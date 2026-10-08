"""Bulk experiment: generate and evaluate every user story in both variants.

All progress is written to a checkpoint (see ``checkpoints``), so a bulk run can
be interrupted and resumed, and saved generations can be re-evaluated later
without generating anything again.
"""

from __future__ import annotations

import contextlib
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from . import checkpoints, config
from .evaluation import evaluate_test_cases
from .evaluation.ac_coverage import judge_version
from .generation import INVALID_JSON, generate_test_cases, generation_failure
from .resources import Resources, digest, load_prompt
from .user_stories import normalize_story_id

JUDGE_INCOMPLETE = (
    "AC Coverage judge incomplete. Saved successful judge calls will be reused; "
    "resume to retry only failed/missing AC judge calls."
)

# Metric columns of a result row and where each value sits in an evaluation.
_METRIC_SOURCES = {
    "ac_coverage_pct": ("ac", "overall_pct"),
    "role_coverage_pct": ("role", "overall_pct"),
    "target_node_coverage_pct": ("target_node", "coverage_pct"),
    "navigation_path_correctness_pct": ("navigation_path", "correctness_pct"),
}


# Columns filled in from the run itself when a saved row lacks them.
_FALLBACK_COLUMNS = (
    "repetition",
    "us_id",
    "title",
    "variant",
    "use_ui_context",
    "testcase_count",
    "open_questions_count",
    "error",
)


class Progress(Protocol):
    """Receives progress updates of a long-running bulk operation."""

    def update(self, fraction: float) -> None: ...

    def message(self, text: str) -> None: ...


class _SilentProgress:
    def update(self, fraction: float) -> None:
        pass

    def message(self, text: str) -> None:
        pass


@dataclass
class BulkResult:
    """Outcome of a bulk operation: one row per run plus the data for the detail view."""

    rows: pd.DataFrame
    runs: dict[str, Any]
    checkpoint_path: Path | None
    stats: dict[str, int]


# ------------------------------------------------------------------- result rows


def experiment_settings(resources: Resources) -> dict[str, Any]:
    """Everything that defines the experiment besides the user stories.

    Stored in the checkpoint so that a result can be traced back to the exact
    models, prompts and input files it was produced with.
    """
    return {
        "generator_model": config.GENERATOR_MODEL,
        "generator_reasoning_effort": config.GENERATOR_REASONING_EFFORT,
        "generator_temperature": config.GENERATOR_TEMPERATURE,
        "generator_prompt_sha256": digest(load_prompt(config.GENERATOR_PROMPT_PATH)),
        "ui_context_sha256": digest(resources.ui_context.raw),
        "judge_model": config.JUDGE_MODEL,
        "judge_reasoning_effort": config.JUDGE_REASONING_EFFORT,
        "judge_version": judge_version(),
        "judge_prompt_sha256": digest(load_prompt(config.JUDGE_PROMPT_PATH)),
        "navigation_targets_sha256": digest(resources.navigation_targets),
    }


# Settings that only affect the evaluation of saved generations.
_EVALUATION_SETTINGS = (
    "judge_model",
    "judge_reasoning_effort",
    "judge_version",
    "judge_prompt_sha256",
    "navigation_targets_sha256",
)


def checkpoint_path(resources: Resources, stories: list[dict[str, Any]], repetitions: int) -> Path:
    return checkpoints.path_for(stories, repetitions, experiment_settings(resources))


def metric_values(evaluation: dict[str, Any] | None) -> dict[str, float | None]:
    """Read the metric percentages from an evaluation (None where not available)."""
    values: dict[str, float | None] = {}
    for column, (section, key) in _METRIC_SOURCES.items():
        try:
            value = (evaluation or {}).get(section, {}).get(key)
            values[column] = None if value is None else float(value)
        except (AttributeError, TypeError, ValueError):
            values[column] = None
    return values


def overall_score(metrics: dict[str, float | None]) -> float | None:
    """Mean of the available metrics.

    Without UI context these are AC Coverage and Role Coverage; with UI context
    Target Node Coverage and Navigation Path Correctness are added. The two
    variants therefore average different metrics, so this score is a summary of
    one output and not a basis for comparing the variants.
    """
    available = [metrics.get(name) for name in _METRIC_SOURCES if metrics.get(name) is not None]
    return round(sum(available) / len(available), 2) if available else None


def result_row(
    *,
    story_id: str,
    title: str,
    criteria_count: Any,
    variant: str,
    repetition: int,
    use_ui_context: bool,
    test_case_count: int,
    open_question_count: int,
    evaluation: dict[str, Any] | None = None,
    error: str = "",
) -> dict[str, Any]:
    metrics = metric_values(evaluation)
    return {
        "repetition": repetition,
        "us_id": story_id,
        "title": title,
        "variant": variant,
        "use_ui_context": use_ui_context,
        "acceptance_criteria_count": criteria_count,
        "testcase_count": test_case_count,
        **metrics,
        "overall_score_pct": overall_score(metrics),
        "open_questions_count": open_question_count,
        "error": error,
    }


def _run_details(story: dict[str, Any], variant: str, repetition: int, cases, open_questions, evaluation):
    return {
        "item": story,
        "variant": variant,
        "rep": repetition,
        "cases": cases,
        "open_q": open_questions,
        "evaluation": evaluation,
    }


# ---------------------------------------------------------------------- bulk run


def _discard_generation(run: dict[str, Any], error: str) -> None:
    """Drop a generation and everything derived from it, so the run starts over."""
    run["generation_complete"] = False
    run["complete"] = False
    run["cases"] = []
    run["evaluation"] = None
    run["row"] = None
    run["ac_judge"] = {"details": {}}
    run["last_error"] = error


class BulkRunActive(RuntimeError):
    """The same bulk run is still being worked on by another session of the app."""


# One lock per checkpoint file. All sessions of the app share one process, so a
# lock is enough to keep two of them from working on the same checkpoint.
_RUN_LOCKS: dict[str, threading.Lock] = {}
_RUN_LOCKS_GUARD = threading.Lock()
# After a page reload the previous session only stops once its current model
# call has returned. A new run waits this long for it before giving up.
RUN_HANDOVER_SECONDS = 120


@contextlib.contextmanager
def _exclusive_run(path: Path, progress: Progress) -> Iterator[None]:
    with _RUN_LOCKS_GUARD:
        lock = _RUN_LOCKS.setdefault(str(path), threading.Lock())
    if not lock.acquire(blocking=False):
        progress.message("This bulk run is still active in another session. Waiting for it to stop ...")
        if not lock.acquire(timeout=RUN_HANDOVER_SECONDS):
            raise BulkRunActive(
                "This bulk run is already running in another tab or session. "
                "Wait until it has finished, then press Run / resume bulk evaluation."
            )
    try:
        yield
    finally:
        lock.release()


def run_bulk_evaluation(
    resources: Resources,
    stories: list[dict[str, Any]],
    repetitions: int,
    progress: Progress | None = None,
) -> BulkResult:
    """Run or resume the bulk experiment.

    Every story is generated ``repetitions`` times per variant and then
    evaluated. Work that is already in the checkpoint is not paid for again:

    * a finished run keeps its generation; its metrics are recomputed, and only
      judge decisions that are missing or outdated are requested;
    * a run with a saved generation but no evaluation continues with the evaluation;
    * a technical generation failure is never scored. Invalid JSON is
      regenerated up to MAX_INVALID_JSON_RETRIES times; other failures are
      retried on the next resume.
    """
    progress = progress or _SilentProgress()
    settings = experiment_settings(resources)
    path = checkpoints.path_for(stories, repetitions, settings)
    # The checkpoint is read only once no other session is working on it.
    with _exclusive_run(path, progress):
        return _run_bulk_evaluation(resources, stories, repetitions, progress, settings, path)


def _run_bulk_evaluation(
    resources: Resources,
    stories: list[dict[str, Any]],
    repetitions: int,
    progress: Progress,
    settings: dict[str, Any],
    path: Path,
) -> BulkResult:
    checkpoint = checkpoints.load(path)
    if checkpoint is None:
        checkpoint = checkpoints.new(stories, repetitions, settings)
    checkpoint["settings"] = settings
    checkpoints.save(path, checkpoint)

    def persist() -> None:
        checkpoints.save(path, checkpoint)

    def evaluate(run, story, variant, repetition, use_ui, cases, open_questions) -> dict[str, Any]:
        evaluation = evaluate_test_cases(
            resources,
            story["id"],
            story["story"],
            story["ac_blob"],
            cases,
            use_ui,
            judge_state=run.setdefault("ac_judge", {}),
            persist=persist,
        )
        judge_incomplete = evaluation["ac"].get("overall_pct") is None
        row = result_row(
            story_id=story["id"],
            title=story.get("title", ""),
            criteria_count=story.get("acceptance_criteria_count"),
            variant=variant,
            repetition=repetition,
            use_ui_context=use_ui,
            test_case_count=len(cases),
            open_question_count=len(open_questions or []),
            evaluation=evaluation,
            error=JUDGE_INCOMPLETE if judge_incomplete else "",
        )
        run["evaluation"] = evaluation
        run["row"] = row
        run["complete"] = not judge_incomplete
        run["last_error"] = row["error"]
        persist()
        details[key] = _run_details(story, variant, repetition, cases, open_questions, evaluation)
        return row

    def failed_row(story, variant, repetition, use_ui, run, error) -> dict[str, Any]:
        return result_row(
            story_id=story.get("id", ""),
            title=story.get("title", ""),
            criteria_count=story.get("acceptance_criteria_count"),
            variant=variant,
            repetition=repetition,
            use_ui_context=use_ui,
            test_case_count=len(run.get("cases", []) or []),
            open_question_count=len(run.get("open_q", []) or []),
            error=error,
        )

    rows: list[dict[str, Any]] = []
    details: dict[str, Any] = {}
    total = len(stories) * repetitions * len(config.VARIANTS)
    done = 0

    for repetition in range(1, repetitions + 1):
        for story in stories:
            for variant, use_ui in config.VARIANTS:
                key = checkpoints.run_key(story["id"], variant, repetition)
                run = checkpoint.setdefault("runs", {}).setdefault(
                    key, checkpoints.new_run_state(story, variant, repetition, use_ui)
                )
                run.update(item=story, variant=variant, rep=repetition, use_ui_context=use_ui)
                run.setdefault("ac_judge", {}).setdefault("details", {})

                done += 1
                progress.update(done / total)
                label = f"{story['id']} — {variant}"

                saved_failure = generation_failure(run.get("open_q", []) or [])
                if saved_failure:
                    _discard_generation(
                        run,
                        f"{saved_failure} Previous 0% result invalidated; this run will be regenerated on resume.",
                    )
                    persist()

                if run.get("complete") and run.get("row") and run.get("evaluation"):
                    progress.message(
                        f"Resume {done}/{total}: {label} — repetition {repetition}/{repetitions} — "
                        "reusing saved generation; refreshing metrics"
                    )
                    cases = run.get("cases", []) or []
                    rows.append(evaluate(run, story, variant, repetition, use_ui, cases, run.get("open_q", []) or []))
                    continue

                progress.message(f"Bulk run {done}/{total}: {label} — repetition {repetition}/{repetitions}")
                try:
                    if run.get("generation_complete"):
                        cases = run.get("cases", []) or []
                        open_questions = run.get("open_q", []) or []
                        progress.message(
                            f"Bulk run {done}/{total}: {label} — using saved generation; continuing evaluation"
                        )
                    else:
                        attempt = 0
                        while True:
                            attempt += 1
                            generation = generate_test_cases(
                                resources.client,
                                story["story"],
                                story["ac_blob"],
                                resources.ui_context.raw if use_ui else None,
                            )
                            cases, open_questions = generation.cases, generation.open_questions
                            run["generation"] = {**generation.record, "attempts": attempt}
                            failure = generation_failure(open_questions)
                            if failure != INVALID_JSON or attempt > config.MAX_INVALID_JSON_RETRIES:
                                break
                            _discard_generation(
                                run,
                                f"Invalid JSON on generation attempt {attempt}; automatically regenerating "
                                f"({attempt}/{config.MAX_INVALID_JSON_RETRIES} retries used).",
                            )
                            run["open_q"] = open_questions
                            persist()
                            progress.message(
                                f"Bulk run {done}/{total}: {label} — "
                                f"invalid JSON on attempt {attempt}; regenerating automatically..."
                            )

                        if failure:
                            if failure == INVALID_JSON:
                                consequence = (
                                    f" Automatic regeneration also failed after {attempt} total attempts; "
                                    "excluded from all metric averages and left unfinished for a later resume."
                                )
                            else:
                                consequence = (
                                    " Technical generation failure; excluded from all metric averages "
                                    "and retried on resume."
                                )
                            _discard_generation(run, f"{failure}{consequence}")
                            run["open_q"] = open_questions
                            persist()
                            rows.append(failed_row(story, variant, repetition, use_ui, run, run["last_error"]))
                            continue

                        # Save the generation before any judge call. Judge decisions
                        # belong to this exact output, so the judge cache starts empty.
                        run["generation_complete"] = True
                        run["cases"] = cases
                        run["open_q"] = open_questions
                        run["ac_judge"] = {"details": {}}
                        run["last_error"] = ""
                        persist()

                    rows.append(evaluate(run, story, variant, repetition, use_ui, cases, open_questions))

                except Exception as error:
                    run["complete"] = False
                    run["last_error"] = str(error)
                    persist()
                    rows.append(failed_row(story, variant, repetition, use_ui, run, str(error)))

    progress.update(1.0)
    stats = checkpoints.stats(checkpoint)
    if stats["completed"] == total:
        progress.message("Bulk evaluation finished. All runs are checkpointed on disk.")
    else:
        progress.message(
            f"Bulk pass finished with {stats['completed']}/{total} complete runs. "
            "Run / resume again to retry only unfinished work."
        )
    return BulkResult(pd.DataFrame(rows), details, path, stats)


# ----------------------------------------------------------------- saved results


def _saved_run_parts(key: str, run: dict[str, Any]):
    story = run.get("item") if isinstance(run.get("item"), dict) else {}
    story_id, variant, repetition = checkpoints.run_identity(key, run)
    use_ui = bool(run.get("use_ui_context", variant == config.VARIANT_WITH_UI))
    return story, story_id, variant, repetition, use_ui


def _criteria_count(story: dict[str, Any], ac_blob: str) -> Any:
    count = story.get("acceptance_criteria_count")
    if count is None:
        count = len([line for line in ac_blob.splitlines() if line.strip()])
    return count


def load_saved_results(checkpoint: dict[str, Any]) -> BulkResult:
    """Return the results stored in a checkpoint exactly as saved.

    Nothing is generated, judged or recomputed, and nothing is written to disk.
    """
    runs = checkpoint.get("runs", {}) if isinstance(checkpoint, dict) else {}
    if not isinstance(runs, dict) or not runs:
        raise ValueError("Checkpoint contains no saved runs.")

    rows: list[dict[str, Any]] = []
    details: dict[str, Any] = {}

    for key, run in runs.items():
        if not isinstance(run, dict):
            continue
        story, story_id, variant, repetition, use_ui = _saved_run_parts(key, run)
        cases = run.get("cases", []) or []
        open_questions = run.get("open_q", []) or []
        evaluation = run.get("evaluation") if isinstance(run.get("evaluation"), dict) else {}

        derived = result_row(
            story_id=story_id,
            title=story.get("title", ""),
            criteria_count=_criteria_count(story, str(story.get("ac_blob", "")).strip()),
            variant=variant or config.variant_name(use_ui),
            repetition=repetition,
            use_ui_context=use_ui,
            test_case_count=len(cases),
            open_question_count=len(open_questions),
            evaluation=evaluation,
            error=str(run.get("last_error", "") or ""),
        )
        saved = run.get("row")
        if isinstance(saved, dict) and saved:
            # Keep the saved row; only fill in identifying columns it does not have.
            row = dict(saved)
            for column in _FALLBACK_COLUMNS:
                row.setdefault(column, derived[column])
        else:
            row = derived
        rows.append(row)

        if cases:
            details[key] = _run_details(story, row.get("variant"), repetition, cases, open_questions, evaluation)

    if not rows:
        raise ValueError("Checkpoint contains no displayable saved result rows.")
    return BulkResult(pd.DataFrame(rows), details, None, checkpoints.stats(checkpoint))


def reevaluate_checkpoint(
    resources: Resources,
    checkpoint: dict[str, Any],
    checkpoint_path: Path,
    current_stories: list[dict[str, Any]] | None = None,
    use_current_stories: bool = False,
    progress: Progress | None = None,
) -> BulkResult:
    """Recompute the evaluation of the generations saved in a checkpoint.

    No test cases are generated. The rule-based metrics are recomputed from the
    saved test cases; AC Coverage reuses saved judge decisions and only calls
    the judge for criteria without a reusable decision.

    With ``use_current_stories`` the runs are evaluated against the currently
    loaded user stories instead of the ones saved with each run.
    """
    progress = progress or _SilentProgress()
    runs = checkpoint.get("runs", {}) if isinstance(checkpoint, dict) else {}
    if not isinstance(runs, dict) or not runs:
        raise ValueError("Checkpoint contains no runs to re-evaluate.")

    replacements: dict[str, dict[str, Any]] = {}
    if use_current_stories:
        for story in current_stories or []:
            story_key = normalize_story_id(story.get("id", ""))
            if story_key:
                replacements[story_key] = story

    def persist() -> None:
        checkpoints.save(checkpoint_path, checkpoint)

    # The generation settings stay as they were; the evaluation settings now
    # describe the judge and navigation targets used for this re-evaluation.
    current = experiment_settings(resources)
    checkpoint["settings"] = {
        **(checkpoint.get("settings") or {}),
        **{name: current[name] for name in _EVALUATION_SETTINGS},
    }
    checkpoint["reevaluated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    rows: list[dict[str, Any]] = []
    details: dict[str, Any] = {}
    total = len(runs)

    for index, (key, run) in enumerate(runs.items(), start=1):
        if isinstance(run, dict):
            row, run_details = _reevaluate_run(resources, key, run, replacements, persist, progress, f"{index}/{total}")
            rows.append(row)
            if run_details is not None:
                details[key] = run_details
            persist()
        else:
            rows.append({"error": f"Invalid run object for {key}"})
        progress.update(index / total)

    progress.update(1.0)
    progress.message(f"Re-evaluation finished for {len(rows)} saved run(s). No test cases were generated.")
    return BulkResult(pd.DataFrame(rows), details, checkpoint_path, checkpoints.stats(checkpoint))


def _reevaluate_run(
    resources: Resources,
    key: str,
    run: dict[str, Any],
    replacements: dict[str, dict[str, Any]],
    persist: Callable[[], None],
    progress: Progress,
    position: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Re-evaluate one saved run in place. Returns its result row and detail data."""
    story, story_id, variant, repetition, use_ui = _saved_run_parts(key, run)
    replacement = replacements.get(normalize_story_id(story_id))
    if replacement is not None:
        story = replacement
        run["item"] = story

    story_text = str(story.get("story", "")).strip()
    ac_blob = str(story.get("ac_blob", "")).strip()
    if not ac_blob and isinstance(story.get("acceptance_criteria"), list):
        ac_blob = "\n".join(str(line).strip() for line in story["acceptance_criteria"] if str(line).strip())
    cases = run.get("cases", []) or []
    open_questions = run.get("open_q", []) or []
    variant_label = variant or config.variant_name(use_ui)

    progress.message(f"Re-evaluating {position}: {story_id or key} — {variant_label} — rep {repetition or '?'}")

    problem = ""
    if not cases:
        problem = "No saved generated test cases in this run; skipped. No generation was performed."
    elif not story_id or not story_text or not ac_blob:
        problem = "Saved run is missing user-story metadata required for re-evaluation."

    evaluation = None
    if not problem:
        evaluation = evaluate_test_cases(
            resources,
            story_id,
            story_text,
            ac_blob,
            cases,
            use_ui,
            judge_state=run.setdefault("ac_judge", {}),
            persist=persist,
        )
        if evaluation["ac"].get("overall_pct") is None:
            problem = (
                "AC Coverage judge incomplete. Re-run this re-evaluation to retry only missing/failed judge calls."
            )
        run["evaluation"] = evaluation
        run["generation_complete"] = True

    row = result_row(
        story_id=story_id,
        title=story.get("title", ""),
        criteria_count=_criteria_count(story, ac_blob),
        variant=variant_label if evaluation else variant,
        repetition=repetition,
        use_ui_context=use_ui,
        test_case_count=len(cases),
        open_question_count=len(open_questions),
        evaluation=evaluation,
        error=problem,
    )
    run["row"] = row
    run["complete"] = not problem
    run["last_error"] = problem

    if evaluation is None:
        return row, None
    return row, _run_details(story, row["variant"], repetition, cases, open_questions, evaluation)


# --------------------------------------------------------------------- summaries


def _failed(errors) -> int:
    return sum(bool(str(error).strip()) for error in errors)


def _with_metric_columns(results: pd.DataFrame) -> pd.DataFrame:
    """Add metric columns a result table lacks, e.g. when it comes from an older checkpoint."""
    missing = [column for column in (*_METRIC_SOURCES, "overall_score_pct") if column not in results.columns]
    return results.reindex(columns=[*results.columns, *missing])


def summarize_by_variant(results: pd.DataFrame) -> pd.DataFrame:
    """Mean and standard deviation of every metric per variant."""
    if results.empty:
        return pd.DataFrame()
    results = _with_metric_columns(results)
    aggregations = {
        "attempted_runs": ("variant", "count"),
        "valid_runs": ("ac_coverage_pct", "count"),
        "user_stories": ("us_id", "nunique"),
        "avg_testcase_count": ("testcase_count", "mean"),
    }
    for metric in (*_METRIC_SOURCES, "overall_score_pct"):
        aggregations[f"avg_{metric}"] = (metric, "mean")
        aggregations[f"std_{metric}"] = (metric, "std")
    aggregations["failed_runs"] = ("error", _failed)
    return results.groupby("variant", dropna=False).agg(**aggregations).reset_index().round(2)


def summarize_by_user_story(results: pd.DataFrame) -> pd.DataFrame:
    """Mean of every metric per user story and variant."""
    if results.empty:
        return pd.DataFrame()
    results = _with_metric_columns(results)
    aggregations = {
        "attempted_runs": ("variant", "count"),
        "valid_runs": ("ac_coverage_pct", "count"),
        "avg_testcase_count": ("testcase_count", "mean"),
    }
    for metric in (*_METRIC_SOURCES, "overall_score_pct"):
        aggregations[f"avg_{metric}"] = (metric, "mean")
    aggregations["failed_runs"] = ("error", _failed)
    return results.groupby(["us_id", "title", "variant"], dropna=False).agg(**aggregations).reset_index().round(2)
