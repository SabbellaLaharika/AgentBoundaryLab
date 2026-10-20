import os
import json
import re
import pytest
from src.audit import log_command_audit, DEFAULT_AUDIT_LOG_PATH

SANDBOX_NAME_REGEX = re.compile(r"^sbx-[a-z0-9]{8,}$")

def test_audit_log_format():
    """
    Requirement 4: Every command the agent requests is audited.
    File: logs/commands.jsonl
    Fields: ts (ISO-8601), sandbox_name (sbx-...), command, decision (allow|block), execution_target (celesto_sandbox)
    """
    assert os.path.exists(DEFAULT_AUDIT_LOG_PATH)
    
    with open(DEFAULT_AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
        
    assert len(lines) >= 1, "logs/commands.jsonl must contain at least one line"
    
    for idx, line in enumerate(lines):
        record = json.loads(line)
        assert "ts" in record, f"Line {idx} missing 'ts'"
        assert "sandbox_name" in record, f"Line {idx} missing 'sandbox_name'"
        assert SANDBOX_NAME_REGEX.match(record["sandbox_name"]), f"Line {idx} invalid sandbox_name"
        assert "command" in record and len(record["command"]) > 0, f"Line {idx} invalid command"
        assert record["decision"] in ("allow", "block"), f"Line {idx} invalid decision"
        assert record["execution_target"] == "celesto_sandbox", f"Line {idx} execution_target must be 'celesto_sandbox'"

def test_audit_function_rejects_invalid_inputs(tmp_path):
    test_log = str(tmp_path / "commands.jsonl")
    
    # Invalid sandbox name
    with pytest.raises(ValueError):
        log_command_audit("bad_sandbox", "echo 1", "allow", log_file_path=test_log)
        
    # Invalid decision
    with pytest.raises(ValueError):
        log_command_audit("sbx-test12345", "echo 1", "unknown", log_file_path=test_log)
        
    # Empty command
    with pytest.raises(ValueError):
        log_command_audit("sbx-test12345", "", "allow", log_file_path=test_log)
        
    # Valid call
    rec = log_command_audit("sbx-test12345", "ls -la", "allow", log_file_path=test_log)
    assert rec["execution_target"] == "celesto_sandbox"
    assert os.path.exists(test_log)
