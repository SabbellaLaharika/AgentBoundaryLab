import os
import json
import re
import pytest
from src.lifecycle import CelestoSandboxContext, generate_sandbox_name, CommandBlockedError
from src.audit import DEFAULT_AUDIT_LOG_PATH
from src.database import get_all_runs

SANDBOX_NAME_REGEX = re.compile(r"^sbx-[a-z0-9]{8,}$")

def test_generate_sandbox_name():
    name = generate_sandbox_name()
    assert SANDBOX_NAME_REGEX.match(name)
    assert name.startswith("sbx-")
    assert len(name) >= 12

def test_lifecycle_success_cleanup():
    sbx_name = "sbx-lifecycle01"
    with CelestoSandboxContext(sandbox_name=sbx_name) as sbx:
        assert sbx.state == "ready"
        res = sbx.run_command("echo 'lifecycle success probe'")
        assert res["execution_target"] == "celesto_sandbox"
        assert sbx.state == "running"
    
    # After exiting with block, cleanup guaranteed
    assert sbx.cleaned_up is True
    assert sbx.state == "deleted"

    runs = [r for r in get_all_runs() if r["sandbox_name"] == sbx_name]
    assert len(runs) > 0
    assert runs[-1]["state"] == "deleted"

def test_lifecycle_failure_cleanup():
    sbx_name = "sbx-lifecycle02"
    with pytest.raises(RuntimeError):
        with CelestoSandboxContext(sandbox_name=sbx_name) as sbx:
            sbx.run_command("python -c 'import sys; sys.exit(0)'")
            raise RuntimeError("Simulated mid-step crash")

    # After exception, cleanup guaranteed
    assert sbx.cleaned_up is True
    assert sbx.state == "deleted"

    runs = [r for r in get_all_runs() if r["sandbox_name"] == sbx_name]
    assert len(runs) > 0
    assert runs[-1]["state"] == "deleted"

def test_lifecycle_interrupt_cleanup():
    sbx_name = "sbx-lifecycle03"
    with pytest.raises(KeyboardInterrupt):
        with CelestoSandboxContext(sandbox_name=sbx_name) as sbx:
            sbx.run_command("sleep 10")
            raise KeyboardInterrupt("Simulated SIGINT / Ctrl-C")

    # After interrupt, cleanup guaranteed
    assert sbx.cleaned_up is True
    assert sbx.state == "deleted"

    runs = [r for r in get_all_runs() if r["sandbox_name"] == sbx_name]
    assert len(runs) > 0
    assert runs[-1]["state"] == "deleted"

def test_lifecycle_report_validity():
    report_path = os.path.join("reports", "lifecycle.json")
    assert os.path.exists(report_path), f"Missing {report_path}"

    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("cleanup_on_success") is True
    assert data.get("cleanup_on_failure") is True
    assert data.get("cleanup_on_interrupt") is True

    sandbox_names = data.get("sandbox_names", [])
    assert isinstance(sandbox_names, list)
    assert len(sandbox_names) >= 1
    # Check uniqueness
    assert len(sandbox_names) == len(set(sandbox_names))

    # All sandbox names must match format
    for name in sandbox_names:
        assert SANDBOX_NAME_REGEX.match(name), f"Invalid sandbox name format: {name}"

    # All sandbox names must appear in command log or reliability file
    with open(DEFAULT_AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
        logged_names = {json.loads(line)["sandbox_name"] for line in f if line.strip()}

    for name in sandbox_names:
        assert name in logged_names, f"Sandbox {name} not found in audit log"
