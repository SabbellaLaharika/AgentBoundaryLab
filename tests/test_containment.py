import os
import json
import pytest

def test_containment_report():
    report_path = os.path.join("reports", "containment.json")
    assert os.path.exists(report_path), f"Missing {report_path}"

    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("attack") in ("prompt_injection_exfil", "destructive_command", "suspicious_package"), \
        f"Invalid attack type: {data.get('attack')}"

    assert data.get("blocked") is True, "blocked must be True"
    assert data.get("host_untouched") is True, "host_untouched must be True"

    evidence_paths = data.get("evidence_paths")
    assert isinstance(evidence_paths, list), "evidence_paths must be a list"
    assert len(evidence_paths) > 0, "evidence_paths must not be empty"

    for p in evidence_paths:
        norm_path = p.replace("/", os.sep)
        assert os.path.exists(norm_path), f"Evidence file does not exist: {norm_path}"
        assert os.path.getsize(norm_path) > 0, f"Evidence file {norm_path} is empty"

def test_containment_log_contents():
    log_path = os.path.join("reports", "evidence", "containment.log")
    assert os.path.exists(log_path)
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "CONTAINMENT BARRIER ENGAGED" in content
    assert "Attack Blocked, Host Untouched" in content
