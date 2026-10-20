import os
import json
import re
from datetime import datetime, timezone
from typing import Literal

SANDBOX_NAME_REGEX = re.compile(r"^sbx-[a-z0-9]{8,}$")
DEFAULT_AUDIT_LOG_PATH = os.path.join("logs", "commands.jsonl")

def log_command_audit(
    sandbox_name: str,
    command: str,
    decision: Literal["allow", "block"],
    log_file_path: str = DEFAULT_AUDIT_LOG_PATH
) -> dict:
    """
    Audits an agent command execution request.
    Strictly satisfies Requirement 4:
    - ts: ISO-8601 string in UTC
    - sandbox_name: matches sbx- plus 8 or more lowercase letters or digits
    - command: non-empty string
    - decision: 'allow' or 'block'
    - execution_target: exact string 'celesto_sandbox'
    """
    if not SANDBOX_NAME_REGEX.match(sandbox_name):
        raise ValueError(f"Invalid sandbox_name '{sandbox_name}': must match 'sbx-[a-z0-9]{{8,}}'")

    if not command or not command.strip():
        raise ValueError("command must be a non-empty string")

    if decision not in ("allow", "block"):
        raise ValueError("decision must be either 'allow' or 'block'")

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "sandbox_name": sandbox_name,
        "command": command.strip(),
        "decision": decision,
        "execution_target": "celesto_sandbox"
    }

    # Ensure parent directory exists
    os.makedirs(os.path.dirname(os.path.abspath(log_file_path)), exist_ok=True)

    # Append JSONL record atomically
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record
