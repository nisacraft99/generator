"""Section 3: run the bulk experiment, re-evaluate saved runs and inspect single runs."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import streamlit as st

from .. import checkpoints, config, experiment
from ..pdf_report import build_pdf
from ..resources import Resources
from ..user_stories import load_user_stories
from .common import StreamlitProgress
from .evaluation_view import render_evaluation

_RESULT_KEYS = (
    "bulk_results_df",
    "bulk_summary_df",
    "bulk_by_us_df",
    "bulk_runs_store",
    "bulk_checkpoint_path",
    "bulk_checkpoint_stats",
)
_SUMMARY_METRICS = (
    ("AC Coverage", "avg_ac_coverage_pct"),
    ("Role Coverage", "avg_role_coverage_pct"),
    ("Target Node Coverage", "avg_target_node_coverage_pct"),
    ("Navigation Path Correctness", "avg_navigation_path_correctness_pct"),
)


def render(resources: Resources) -> None:
    st.markdown("---")
    st.subheader("Bulk Evaluation")
    st.write(
        "This runs all user stories in a bulk JSON file. For every user story, the tool generates "
        "test cases once without UI context and once with UI context. You can repeat the whole run "
        "multiple times to get more stable average scores."
    )

    repetitions = int(
        st.number_input(
            "How many repetitions per variant?",
            min_value=1,
            max_value=20,
            value=3,
            step=1,
            help="Example: 3 repetitions with 24 user stories means 24 × 2 variants × 3 = 144 LLM calls.",
        )
    )
    stories_upload = st.file_uploader(
        f"Optional: upload {config.USER_STORIES_PATH.name}. If nothing is uploaded, the app uses the "
        f"local file in the {config.DATA_DIR.name} folder.",
        type=["json"],
        key="bulk_userstories_upload",
    )

    uploaded_checkpoint, use_current_stories, show_saved, reevaluate = _render_reevaluation_controls()
    stories = _preview_stories(stories_upload)

    if show_saved and uploaded_checkpoint is not None:
        _show_saved_results(uploaded_checkpoint)
    if reevaluate and uploaded_checkpoint is not None:
        _reevaluate(resources, uploaded_checkpoint, stories, use_current_stories)

    _render_run_controls(resources, stories, stories_upload, repetitions)
    _render_summary()
    _render_downloads()
    _render_run_details(resources)


# ------------------------------------------------------------------------ inputs


def _render_reevaluation_controls():
    st.markdown("#### Re-evaluate already generated runs")
    st.caption(
        "Use this when you already have a bulk checkpoint/run JSON and only want to recompute the evaluation. "
        "This path never generates new test cases."
    )
    upload = st.file_uploader(
        "Upload existing bulk checkpoint / runs JSON",
        type=["json"],
        key="bulk_existing_runs_upload",
        help="Upload a file created by 'Download bulk checkpoint backup' "
        "(or a compatible JSON containing a top-level runs object).",
    )
    use_current_stories = st.checkbox(
        "Use the currently loaded bulk_userstories definitions for re-evaluation",
        value=False,
        help=(
            "Leave this off when you only changed navigation_targets.json or the evaluation logic and want to "
            "keep the original experiment input. Turn it on only if AC Coverage and Role Coverage should be "
            "evaluated against the currently loaded user-story definitions."
        ),
    )

    checkpoint = None
    if upload is not None:
        try:
            checkpoint = checkpoints.read_upload(upload)
            upload.seek(0)
            st.info(
                f"Uploaded checkpoint contains {len(checkpoint.get('runs', {}))} saved run(s); "
                f"{checkpoints.stats(checkpoint)['generated']} have saved generations. "
                "No generation will be performed by the re-evaluation button."
            )
        except Exception as error:
            st.error(f"Could not read uploaded checkpoint: {error}")

    show_column, reevaluate_column = st.columns(2)
    with show_column:
        show_saved = st.button(
            "Show saved results (NO API CALLS)",
            disabled=checkpoint is None,
            type="primary",
            help=(
                "Displays the metrics and judge decisions already stored in the uploaded checkpoint. "
                "Nothing is regenerated or re-evaluated."
            ),
        )
    with reevaluate_column:
        reevaluate = st.button(
            "Re-evaluate uploaded runs only (NO generation)",
            disabled=checkpoint is None,
            type="secondary",
            help=(
                "Recomputes the evaluation of the saved generations. "
                "AC Coverage may call the currently configured LLM judge."
            ),
        )
    return checkpoint, use_current_stories, show_saved, reevaluate


def _preview_stories(stories_upload: Any) -> list[dict[str, Any]]:
    """Load the user stories of the next bulk run: the upload if present, else the local file."""
    local_name = config.USER_STORIES_PATH.name
    try:
        if stories_upload is not None:
            stories = load_user_stories(stories_upload)
            stories_upload.seek(0)
            st.info(f"Uploaded bulk file contains {len(stories)} user stories.")
            return stories
        if config.USER_STORIES_PATH.exists():
            stories = load_user_stories(config.USER_STORIES_PATH)
            st.info(f"Local {local_name} contains {len(stories)} user stories.")
            return stories
        st.warning(f"No uploaded file and no local {local_name} found.")
    except Exception as error:
        st.error(f"Could not preview bulk user stories: {error}")
    return []


# ----------------------------------------------------------------------- actions


def _store(result: experiment.BulkResult, keep_checkpoint_path: bool = True) -> None:
    state = st.session_state
    state.bulk_results_df = result.rows
    state.bulk_summary_df = experiment.summarize_by_variant(result.rows)
    state.bulk_by_us_df = experiment.summarize_by_user_story(result.rows)
    state.bulk_runs_store = result.runs
    state.bulk_checkpoint_stats = result.stats
    if keep_checkpoint_path:
        state.bulk_checkpoint_path = result.checkpoint_path


def _show_saved_results(checkpoint: dict[str, Any]) -> None:
    try:
        result = experiment.load_saved_results(checkpoint)
        # Viewing an upload must not point the download button at a file on disk.
        _store(result, keep_checkpoint_path=False)
        st.success(
            f"Loaded {len(result.rows)} saved run(s) exactly as stored in the uploaded checkpoint. "
            "No API calls, no generation, and no re-evaluation were performed."
        )
    except Exception as error:
        st.error(f"Could not display saved checkpoint results: {error}")


def _reevaluate(
    resources: Resources, uploaded: dict[str, Any], stories: list[dict[str, Any]], use_current_stories: bool
) -> None:
    try:
        # Work on a local copy of the upload. If an earlier re-evaluation was
        # interrupted, continue from that copy instead of starting over.
        path = checkpoints.path_for_upload(uploaded)
        checkpoint = checkpoints.load(path)
        if checkpoint is None:
            checkpoint = uploaded
            checkpoints.save(path, checkpoint)

        with st.spinner("Re-evaluating saved generations only. No test-case generation calls are made."):
            result = experiment.reevaluate_checkpoint(
                resources,
                checkpoint,
                path,
                current_stories=stories,
                use_current_stories=use_current_stories,
                progress=StreamlitProgress(),
            )
        _store(result)
        st.success(
            f"Re-evaluated {len(result.rows)} saved run(s). No test cases were generated. "
            "The updated checkpoint can be downloaded below."
        )
    except Exception as error:
        st.error(f"Re-evaluation of uploaded runs failed: {error}")


def _render_run_controls(
    resources: Resources, stories: list[dict[str, Any]], stories_upload: Any, repetitions: int
) -> None:
    variant_count = len(config.VARIANTS)
    generation_calls = len(stories) * repetitions * variant_count
    judge_calls = sum(story.get("acceptance_criteria_count", 0) for story in stories) * repetitions * variant_count
    st.caption(
        f"Maximum calls for a completely new run: {generation_calls + judge_calls} "
        f"({generation_calls} generation + {judge_calls} AC Coverage judge calls). "
        "Resume mode does not repeat already checkpointed work."
    )

    checkpoint_path = experiment.checkpoint_path(resources, stories, repetitions) if stories else None
    checkpoint = checkpoints.load(checkpoint_path)
    if checkpoint:
        stats = checkpoints.stats(checkpoint)
        st.success(
            f"Saved checkpoint found: {stats['completed']}/{generation_calls} runs complete; "
            f"{stats['generated']} generations already saved; "
            f"{stats['judge_done']} AC judge decisions already saved. "
            "Starting again will resume from this checkpoint instead of paying for those calls again."
        )
        if stats["judge_failed"]:
            st.warning(
                f"{stats['judge_failed']} AC judge call(s) previously failed. "
                "Only those failed/missing judge calls will be retried."
            )

    run_column, clear_column = st.columns([2, 1])
    with run_column:
        run_clicked = st.button(
            "Run / resume bulk evaluation", disabled=not (resources.client and stories), type="primary"
        )
    with clear_column:
        clear_clicked = st.button(
            "Clear saved checkpoint",
            disabled=not bool(checkpoint),
            help="Deletes saved bulk progress for the currently selected dataset and repetition count. "
            "Use only when you intentionally want to start from scratch.",
        )

    if clear_clicked and checkpoint_path:
        checkpoints.delete(checkpoint_path)
        for key in _RESULT_KEYS:
            st.session_state.pop(key, None)
        st.success("Saved checkpoint cleared. The next run will start from scratch.")
        st.rerun()

    if run_clicked:
        try:
            if stories_upload is not None:
                stories_upload.seek(0)
                run_stories = load_user_stories(stories_upload)
            else:
                run_stories = load_user_stories(config.USER_STORIES_PATH)

            with st.spinner(
                "Running/resuming bulk evaluation. Completed generations and AC judge calls are reused from disk."
            ):
                result = experiment.run_bulk_evaluation(resources, run_stories, repetitions, StreamlitProgress())
            _store(result)
            st.success(
                f"Checkpoint saved: {result.stats.get('completed', 0)}/"
                f"{len(run_stories) * repetitions * variant_count} runs complete. "
                "If the app stops, rerun with the same dataset and repetition count and press Run / resume."
            )
        except Exception as error:
            st.error(
                f"Bulk evaluation stopped: {error}. Progress already written to the checkpoint remains "
                "available. Press Run / resume bulk evaluation to continue without repeating completed work."
            )


# ----------------------------------------------------------------------- results


def _percent(value: Any) -> str:
    try:
        return "N/A" if pd.isna(value) else f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return "N/A"


def _render_variant_summary(summary: pd.DataFrame, variant: str, title: str) -> None:
    st.markdown(f"#### {title}")
    rows = summary[summary["variant"] == variant]
    if rows.empty:
        st.warning(f"No results for {variant}.")
        return
    row = rows.iloc[0]
    for label, column in _SUMMARY_METRICS:
        st.metric(label, _percent(row[column]))
    if variant == config.VARIANT_WITHOUT_UI:
        st.caption(
            "Target Node Coverage and Navigation Path Correctness are N/A here: "
            "without UI context, no ui_node_id values are generated."
        )
    st.metric("Overall Score", _percent(row["avg_overall_score_pct"]))


def _render_summary() -> None:
    summary = st.session_state.get("bulk_summary_df")
    if summary is None or summary.empty:
        return
    st.subheader("Bulk Summary")

    failed = int(summary["failed_runs"].fillna(0).sum()) if "failed_runs" in summary.columns else 0
    if failed:
        st.warning(
            f"{failed} technical/incomplete bulk run(s) are excluded from metric averages. "
            "Use Run / resume bulk evaluation to retry only those unfinished runs. "
            "Invalid JSON is never counted as 0% quality."
        )

    st.markdown("### Variant comparison")
    with_column, without_column = st.columns(2)
    with with_column:
        _render_variant_summary(summary, config.VARIANT_WITH_UI, "With UI Context")
    with without_column:
        _render_variant_summary(summary, config.VARIANT_WITHOUT_UI, "Without UI Context")
    st.info(
        "Overall Score is the average of AC Coverage, Role Coverage, Target Node Coverage and Navigation Path "
        "Correctness, as far as they are available. Without UI context only the first two exist, so the score "
        "summarises one variant and is not a basis for comparing the two."
    )

    st.markdown("### Summary table")
    st.dataframe(summary, width="stretch")
    _csv_download("download bulk summary CSV", summary, "bulk_evaluation_summary.csv")


def _csv_download(label: str, frame: pd.DataFrame, file_name: str) -> None:
    st.download_button(label, data=frame.to_csv(index=False).encode("utf-8"), file_name=file_name, mime="text/csv")


def _render_downloads() -> None:
    state = st.session_state
    by_story = state.get("bulk_by_us_df")
    if by_story is not None and not by_story.empty:
        with st.expander("Bulk results by User Story"):
            st.dataframe(by_story, width="stretch")
            _csv_download("download user-story summary CSV", by_story, "bulk_evaluation_by_user_story.csv")

    checkpoint_path = state.get("bulk_checkpoint_path")
    if checkpoint_path and os.path.exists(checkpoint_path):
        try:
            with open(checkpoint_path, "rb") as handle:
                st.download_button(
                    "Download bulk checkpoint backup",
                    data=handle.read(),
                    file_name=os.path.basename(checkpoint_path),
                    mime="application/json",
                    help="Backup of all saved generations and AC judge decisions from the current bulk run.",
                )
        except OSError as error:
            st.warning(f"Could not prepare checkpoint download: {error}")

    results = state.get("bulk_results_df")
    if results is not None and not results.empty:
        with st.expander("Raw bulk result rows"):
            st.dataframe(results, width="stretch")
            _csv_download("download raw bulk results CSV", results, "bulk_evaluation_raw_results.csv")


def _render_run_details(resources: Resources) -> None:
    """Metric details and PDF export for one selected run of the last bulk result."""
    runs = st.session_state.get("bulk_runs_store")
    if not runs:
        return
    st.markdown("---")
    st.subheader("Bulk Run Details")
    st.write(
        "Select a User Story, variant and repetition to inspect every metric and its reasons, "
        "or export the corresponding PDF."
    )

    results = st.session_state.bulk_results_df
    story_column, variant_column, repetition_column = st.columns(3)
    with story_column:
        story_id = st.selectbox("User Story", sorted(results["us_id"].unique().tolist()), key="bulk_pdf_us")
    with variant_column:
        variant = st.selectbox("Variant", [config.VARIANT_WITH_UI, config.VARIANT_WITHOUT_UI], key="bulk_pdf_var")
    with repetition_column:
        repetition = st.selectbox("Repetition", sorted(results["repetition"].unique().tolist()), key="bulk_pdf_rep")

    key = checkpoints.run_key(story_id, variant, repetition)
    run = runs.get(key)
    if not run or "cases" not in run:
        st.warning(f"No data available for {key}. This run may have failed.")
        return

    st.caption(f"Generated test cases: {len(run['cases'])}")
    render_evaluation(
        resources.ui_context,
        run["evaluation"],
        f"Evaluation details — {story_id} / {variant} / repetition {repetition}",
    )
    story = run["item"]
    st.download_button(
        f"Download PDF — {story_id} / {variant} / rep {repetition}",
        data=build_pdf(
            story["story"],
            story["ac_blob"],
            run["cases"],
            run["open_q"],
            evaluation=run["evaluation"],
            story_id=story["id"],
        ),
        file_name=f"test_design_{story_id}_{variant}_rep{repetition}.pdf",
        mime="application/pdf",
        key="bulk_pdf_download",
    )
