import os
import json
import re
import pytest

SANDBOX_NAME_REGEX = re.compile(r"^sbx-[a-z0-9]{8,}$")

def test_failure_policy_report():
    policy_path = os.path.join("reports", "failure_policy.json")
    assert os.path.exists(policy_path), f"Missing {policy_path}"

    with open(policy_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("failed_step") == 7, "failed_step must be 7"
    assert data.get("total_steps") == 10, "total_steps must be 10"
    assert data.get("policy") in ("resume", "rollback", "fresh"), "policy must be resume, rollback, or fresh"
    
    rationale = data.get("rationale", "")
    assert isinstance(rationale, str), "rationale must be string"
    assert len(rationale) >= 200, f"rationale must be >= 200 chars, got {len(rationale)}"

    trace_path = data.get("trace_path")
    assert trace_path == "reports/failure_trace.jsonl", "trace_path must be reports/failure_trace.jsonl"
    assert os.path.exists(trace_path), f"Trace file {trace_path} does not exist"

def test_failure_trace_file():
    trace_path = os.path.join("reports", "failure_trace.jsonl")
    assert os.path.exists(trace_path), f"Missing {trace_path}"

    with open("reports/failure_policy.json", "r", encoding="utf-8") as f:
        policy_data = json.load(f)
    expected_policy = policy_data["policy"]

    with open(trace_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) > 0, "failure_trace.jsonl must not be empty"

    policy_applied_found = False
    for line in lines:
        entry = json.loads(line)
        assert "ts" in entry
        assert "sandbox_name" in entry
        assert SANDBOX_NAME_REGEX.match(entry["sandbox_name"])
        assert "event" in entry

        if entry.get("event") == "policy_applied":
            policy_applied_found = True
            assert entry.get("policy") == expected_policy, f"policy_applied policy mismatch: expected {expected_policy}, got {entry.get('policy')}"
            assert entry.get("failed_step") == 7

    assert policy_applied_found, "failure_trace.jsonl must contain an event='policy_applied' line"
