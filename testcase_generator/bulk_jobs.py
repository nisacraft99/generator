"""Bulk runs and re-evaluations in a background thread, independent of the browser.

Streamlit stops a running script as soon as the browser disconnects: a closed
tab, a reloaded page or a computer going to sleep. A bulk run or the
re-evaluation of a whole checkpoint takes hours, so it runs in a thread of its
own. The thread keeps working while nobody watches, and every session of the
app can show its progress.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import checkpoints, config, experiment
from .resources import Resources


@dataclass
class BulkJob:
    """One background job. Also serves as its progress display."""

    checkpoint_path: Path
    kind: str  # BULK_RUN or REEVALUATION
    description: str
    total_runs: int
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    fraction: float = 0.0
    status: str = "Starting ..."
    result: experiment.BulkResult | None = None
    error: str | None = None
    thread: threading.Thread | None = field(default=None, repr=False)

    @property
    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def update(self, fraction: float) -> None:
        self.fraction = min(max(float(fraction), 0.0), 1.0)

    def message(self, text: str) -> None:
        self.status = text


BULK_RUN = "bulk run"
REEVALUATION = "re-evaluation"

_jobs: dict[str, BulkJob] = {}
_jobs_guard = threading.Lock()


def _launch(job: BulkJob, task: Callable[[BulkJob], experiment.BulkResult]) -> BulkJob:
    def work() -> None:
        try:
            job.result = task(job)
        except Exception as error:
            job.error = str(error)
        finally:
            job.finished_at = datetime.now(timezone.utc)

    job.thread = threading.Thread(target=work, name=f"{job.kind}-{job.checkpoint_path.stem}", daemon=True)
    _jobs[str(job.checkpoint_path)] = job
    job.thread.start()
    return job


def start(resources: Resources, stories: list[dict[str, Any]], repetitions: int) -> BulkJob:
    """Start the bulk run in the background, or return it if it is already running."""
    path = experiment.checkpoint_path(resources, stories, repetitions)
    with _jobs_guard:
        job = _jobs.get(str(path))
        if job is not None and job.running:
            return job
        total = len(stories) * int(repetitions) * len(config.VARIANTS)
        job = BulkJob(
            checkpoint_path=path,
            kind=BULK_RUN,
            description=f"{len(stories)} user stories × {repetitions} repetitions × {len(config.VARIANTS)} variants",
            total_runs=total,
        )
        return _launch(job, lambda job: experiment.run_bulk_evaluation(resources, stories, repetitions, progress=job))


def start_reevaluation(
    resources: Resources,
    uploaded: dict[str, Any],
    current_stories: list[dict[str, Any]],
    use_current_stories: bool,
) -> BulkJob:
    """Re-evaluate an uploaded checkpoint in the background, or return the job if it is already running.

    The work happens on a local copy of the upload. If an earlier re-evaluation
    of the same upload was interrupted, it continues from that copy.
    """
    path = checkpoints.path_for_upload(uploaded)
    with _jobs_guard:
        job = _jobs.get(str(path))
        if job is not None and job.running:
            return job
        checkpoint = checkpoints.load(path)
        if checkpoint is None:
            checkpoint = uploaded
            checkpoints.save(path, checkpoint)
        runs = len(checkpoint.get("runs", {}) or {})
        job = BulkJob(
            checkpoint_path=path,
            kind=REEVALUATION,
            description=f"re-evaluation of {runs} saved runs (no generation)",
            total_runs=runs,
        )
        return _launch(
            job,
            lambda job: experiment.reevaluate_checkpoint(
                resources,
                checkpoint,
                path,
                current_stories=current_stories,
                use_current_stories=use_current_stories,
                progress=job,
            ),
        )


def running() -> BulkJob | None:
    """The job that is currently working, if any."""
    with _jobs_guard:
        active = [job for job in _jobs.values() if job.running]
    return max(active, key=lambda job: job.started_at) if active else None


def latest() -> BulkJob | None:
    """The job started last in this app process, running or finished."""
    with _jobs_guard:
        jobs = list(_jobs.values())
    return max(jobs, key=lambda job: job.started_at) if jobs else None
