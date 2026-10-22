import os
import json
import re
from datetime import datetime
import pytest

SANDBOX_NAME_REGEX = re.compile(r"^sbx-[a-z0-9]{8,}$")

def test_concurrency_report():
    report_path = os.path.join("reports", "concurrency.json")
    assert os.path.exists(report_path), f"Missing {report_path}"

    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    jobs = data.get("jobs", [])
    assert isinstance(jobs, list), "jobs must be a list"
    assert len(jobs) >= 5, f"Must have at least 5 jobs, got {len(jobs)}"

    sandbox_names = []
    for idx, job in enumerate(jobs):
        assert "sandbox_name" in job, f"Job {idx} missing sandbox_name"
        name = job["sandbox_name"]
        assert SANDBOX_NAME_REGEX.match(name), f"Job {idx} invalid sandbox_name '{name}'"
        sandbox_names.append(name)

        assert "started_at" in job, f"Job {idx} missing started_at"
        # Validate ISO-8601 format
        dt = datetime.fromisoformat(job["started_at"])
        assert dt is not None

    # Uniqueness check
    assert len(sandbox_names) == len(set(sandbox_names)), "All sandbox_names in concurrency jobs must be unique"

    breakage_notes = data.get("breakage_notes", "")
    assert isinstance(breakage_notes, str), "breakage_notes must be a string"
    assert len(breakage_notes) >= 40, f"breakage_notes must be >= 40 chars, got {len(breakage_notes)}"
