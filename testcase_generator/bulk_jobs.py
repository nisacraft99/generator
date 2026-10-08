"""Bulk runs in a background thread, independent of the browser.

Streamlit stops a running script as soon as the browser disconnects: a closed
tab, a reloaded page or a computer going to sleep. A bulk run takes hours, so
it runs in a thread of its own. The thread keeps working while nobody watches,
and every session of the app can show its progress.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config, experiment
from .resources import Resources


@dataclass
class BulkJob:
    """One bulk run in the background. Also serves as its progress display."""

    checkpoint_path: Path
    story_count: int
    repetitions: int
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    fraction: float = 0.0
    status: str = "Starting ..."
    result: experiment.BulkResult | None = None
    error: str | None = None
    thread: threading.Thread | None = field(default=None, repr=False)

    @property
    def total_runs(self) -> int:
        return self.story_count * self.repetitions * len(config.VARIANTS)

    @property
    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def update(self, fraction: float) -> None:
        self.fraction = min(max(float(fraction), 0.0), 1.0)

    def message(self, text: str) -> None:
        self.status = text


_jobs: dict[str, BulkJob] = {}
_jobs_guard = threading.Lock()


def start(resources: Resources, stories: list[dict[str, Any]], repetitions: int) -> BulkJob:
    """Start the bulk run in the background, or return it if it is already running."""
    path = experiment.checkpoint_path(resources, stories, repetitions)
    with _jobs_guard:
        job = _jobs.get(str(path))
        if job is not None and job.running:
            return job

        job = BulkJob(checkpoint_path=path, story_count=len(stories), repetitions=int(repetitions))

        def work() -> None:
            try:
                job.result = experiment.run_bulk_evaluation(resources, stories, repetitions, progress=job)
            except Exception as error:
                job.error = str(error)
            finally:
                job.finished_at = datetime.now(timezone.utc)

        job.thread = threading.Thread(target=work, name=f"bulk-run-{path.stem}", daemon=True)
        _jobs[str(path)] = job
        job.thread.start()
    return job


def running() -> BulkJob | None:
    """The bulk run that is currently working, if any."""
    with _jobs_guard:
        active = [job for job in _jobs.values() if job.running]
    return max(active, key=lambda job: job.started_at) if active else None


def latest() -> BulkJob | None:
    """The bulk run started last in this app process, running or finished."""
    with _jobs_guard:
        jobs = list(_jobs.values())
    return max(jobs, key=lambda job: job.started_at) if jobs else None
