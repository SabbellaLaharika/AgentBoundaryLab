import os
import json
import re
from datetime import datetime
import pytest

SANDBOX_NAME_REGEX = re.compile(r"^sbx-[a-z0-9]{8,}$")
ALLOWED_CAPABILITY_IDS = {
    "persistence", "snapshots", "celestofs", "browser",
    "published_ports", "network_policy", "safety_hooks",
    "host_mounts", "coding_agent_preset", "agentor_durable"
}

def test_secret_hygiene():
    """Requirement: No committed secrets. .env must not exist in repository."""
    assert not os.path.exists(".env"), "Forbidden: .env file must NOT exist in the repository"
    assert os.path.exists(".env.example"), "Missing .env.example"
    with open(".env.example", "r", encoding="utf-8") as f:
        content = f.read()
    for key in ["CELESTO_PROVIDER", "CELESTO_API_KEY", "LLM_API_KEY", "DATABASE_URL"]:
        assert key in content, f".env.example missing key {key}"

def test_problem_report_compliance():
    """reports/problem.json: who (>=40), agent_work (>=40), proof_output (>=20), idea_source."""
    path = os.path.join("reports", "problem.json")
    assert os.path.exists(path), "Missing reports/problem.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data.get("who"), str) and len(data["who"]) >= 40, "who must be >= 40 chars"
    assert isinstance(data.get("agent_work"), str) and len(data["agent_work"]) >= 40, "agent_work must be >= 40 chars"
    assert isinstance(data.get("proof_output"), str) and len(data["proof_output"]) >= 20, "proof_output must be >= 20 chars"
    assert data.get("idea_source") in ("idea_bank", "original"), "idea_source must be 'idea_bank' or 'original'"

def test_capabilities_report_compliance():
    """reports/capabilities.json: >=2 objects, valid unique ids, why >= 80 chars, evidence_path exists."""
    path = os.path.join("reports", "capabilities.json")
    assert os.path.exists(path), "Missing reports/capabilities.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    caps = data.get("capabilities", [])
    assert isinstance(caps, list) and len(caps) >= 2, "capabilities must have at least 2 objects"

    ids = [c.get("id") for c in caps]
    assert len(ids) == len(set(ids)), "capability ids must be unique"

    for c in caps:
        cid = c.get("id")
        assert cid in ALLOWED_CAPABILITY_IDS, f"Invalid capability id '{cid}'"
        why = c.get("why", "")
        assert isinstance(why, str) and len(why) >= 80, f"Capability {cid} 'why' must be >= 80 chars"
        ev_path = c.get("evidence_path", "").replace("/", os.sep)
        assert os.path.exists(ev_path), f"Evidence path for {cid} does not exist: {ev_path}"

def test_lifecycle_report_compliance():
    """reports/lifecycle.json: cleanup flags true, unique sandbox names appearing in audit log or reliability."""
    path = os.path.join("reports", "lifecycle.json")
    assert os.path.exists(path), "Missing reports/lifecycle.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("cleanup_on_success") is True
    assert data.get("cleanup_on_failure") is True
    assert data.get("cleanup_on_interrupt") is True

    names = data.get("sandbox_names", [])
    assert isinstance(names, list) and len(names) >= 1
    assert len(names) == len(set(names)), "sandbox_names must be unique"

    # Read audit log names
    with open(os.path.join("logs", "commands.jsonl"), "r", encoding="utf-8") as f:
        logged_names = {json.loads(line)["sandbox_name"] for line in f if line.strip()}

    for name in names:
        assert SANDBOX_NAME_REGEX.match(name), f"Invalid sandbox_name format: {name}"
        assert name in logged_names, f"Sandbox {name} not found in command log"

def test_commands_audit_log_compliance():
    """logs/commands.jsonl: ts, sandbox_name, command, decision (allow|block), execution_target (celesto_sandbox)."""
    path = os.path.join("logs", "commands.jsonl")
    assert os.path.exists(path), "Missing logs/commands.jsonl"
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) >= 1, "logs/commands.jsonl must have at least 1 line"
    for idx, line in enumerate(lines):
        rec = json.loads(line)
        assert "ts" in rec, f"Line {idx} missing ts"
        assert SANDBOX_NAME_REGEX.match(rec["sandbox_name"]), f"Line {idx} invalid sandbox_name"
        assert rec["command"], f"Line {idx} command must be non-empty"
        assert rec["decision"] in ("allow", "block"), f"Line {idx} decision must be allow or block"
        assert rec["execution_target"] == "celesto_sandbox", f"Line {idx} execution_target must be celesto_sandbox"

def test_containment_report_compliance():
    """reports/containment.json: attack type, blocked: true, host_untouched: true, evidence_paths exist."""
    path = os.path.join("reports", "containment.json")
    assert os.path.exists(path), "Missing reports/containment.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("attack") in ("prompt_injection_exfil", "destructive_command", "suspicious_package")
    assert data.get("blocked") is True
    assert data.get("host_untouched") is True

    paths = data.get("evidence_paths", [])
    assert isinstance(paths, list) and len(paths) >= 1
    for p in paths:
        norm_p = p.replace("/", os.sep)
        assert os.path.exists(norm_p), f"Evidence file does not exist: {norm_p}"

def test_failure_policy_and_trace_compliance():
    """reports/failure_policy.json & reports/failure_trace.jsonl: step 7 of 10, policy, rationale >= 200, trace match."""
    policy_path = os.path.join("reports", "failure_policy.json")
    assert os.path.exists(policy_path), "Missing reports/failure_policy.json"
    with open(policy_path, "r", encoding="utf-8") as f:
        pdata = json.load(f)

    assert pdata.get("failed_step") == 7
    assert pdata.get("total_steps") == 10
    policy = pdata.get("policy")
    assert policy in ("resume", "rollback", "fresh")
    assert isinstance(pdata.get("rationale"), str) and len(pdata["rationale"]) >= 200

    trace_path = pdata.get("trace_path", "").replace("/", os.sep)
    assert os.path.exists(trace_path), f"Trace file does not exist: {trace_path}"
    with open(trace_path, "r", encoding="utf-8") as f:
        trace_lines = [json.loads(line) for line in f if line.strip()]

    policy_applied_events = [e for e in trace_lines if e.get("event") == "policy_applied" and e.get("policy") == policy]
    assert len(policy_applied_events) >= 1, f"Trace missing event: policy_applied with policy: {policy}"

def test_concurrency_report_compliance():
    """reports/concurrency.json: >=5 jobs, unique sandbox_name, started_at ISO-8601, breakage_notes >= 40 chars."""
    path = os.path.join("reports", "concurrency.json")
    assert os.path.exists(path), "Missing reports/concurrency.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    jobs = data.get("jobs", [])
    assert len(jobs) >= 5, f"Expected >= 5 jobs, got {len(jobs)}"

    names = [j["sandbox_name"] for j in jobs]
    assert len(names) == len(set(names)), "Job sandbox_names must be unique"
    for j in jobs:
        assert SANDBOX_NAME_REGEX.match(j["sandbox_name"])
        datetime.fromisoformat(j["started_at"])

    notes = data.get("breakage_notes", "")
    assert isinstance(notes, str) and len(notes) >= 40, "breakage_notes must be >= 40 chars"

def test_reliability_report_and_math_compliance():
    """reports/reliability.json: run_count >= 20, math percentiles, sorted wall_clock_s, postmortem >= 200 chars."""
    path = os.path.join("reports", "reliability.json")
    assert os.path.exists(path), "Missing reports/reliability.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    run_count = data.get("run_count")
    runs = data.get("runs", [])
    assert run_count >= 20 and len(runs) == run_count

    wall_clocks = [r["wall_clock_s"] for r in runs]
    assert wall_clocks == sorted(wall_clocks), "runs must be sorted by wall_clock_s ascending"

    # Verify median (mean of 10th and 11th)
    expected_median_wc = round((wall_clocks[9] + wall_clocks[10]) / 2.0, 4)
    assert abs(data["median_wall_clock_s"] - expected_median_wc) < 0.001

    # Verify p90 (18th item)
    expected_p90_wc = round(wall_clocks[17], 4)
    assert abs(data["p90_wall_clock_s"] - expected_p90_wc) < 0.001

    # Verify postmortem
    pm_path = data.get("postmortem_path", "").replace("/", os.sep)
    assert os.path.exists(pm_path)
    with open(pm_path, "r", encoding="utf-8") as f:
        pm_content = f.read()
    assert len(pm_content) >= 200, "postmortem must be >= 200 chars"
