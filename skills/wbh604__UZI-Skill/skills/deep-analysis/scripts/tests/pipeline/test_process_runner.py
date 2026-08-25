"""Issue #95 hard-timeout regressions."""
from __future__ import annotations

import operator
import time


def test_process_jobs_terminate_timed_out_worker_and_return_fast():
    from lib.pipeline.process_runner import ProcessJob, run_process_jobs

    jobs = [
        ProcessJob(key="fast", target=operator.add, args=(1, 2), timeout_sec=1.0),
        ProcessJob(key="slow", target=time.sleep, args=(10.0,), timeout_sec=0.05),
    ]

    started = time.monotonic()
    outcomes = {item.key: item for item in run_process_jobs(jobs, max_workers=2, overall_timeout=1.0)}
    elapsed = time.monotonic() - started

    assert elapsed < 1.0
    assert outcomes["fast"].value == 3
    assert outcomes["fast"].error is None
    assert outcomes["slow"].timed_out is True
    assert "timeout" in outcomes["slow"].error


def test_process_jobs_serialize_members_of_same_group():
    from lib.pipeline.process_runner import ProcessJob, run_process_jobs

    jobs = [
        ProcessJob(key="mini-a", target=time.sleep, args=(0.08,), timeout_sec=1.0, serial_group="mini"),
        ProcessJob(key="mini-b", target=time.sleep, args=(0.08,), timeout_sec=1.0, serial_group="mini"),
        ProcessJob(key="regular", target=time.sleep, args=(0.08,), timeout_sec=1.0),
    ]

    started = time.monotonic()
    outcomes = run_process_jobs(jobs, max_workers=3, overall_timeout=2.0)
    elapsed = time.monotonic() - started

    assert len(outcomes) == 3
    assert all(item.error is None for item in outcomes)
    assert 0.14 <= elapsed < 1.5
