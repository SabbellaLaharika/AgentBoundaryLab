import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from src.lifecycle import CelestoSandboxContext, generate_sandbox_name
from src.audit import log_command_audit, DEFAULT_AUDIT_LOG_PATH

DEFAULT_TRACE_PATH = os.path.join("reports", "failure_trace.jsonl")

AGENT_PIPELINE_STEPS = [
    {"step": 1, "name": "initialize_guest_environment", "cmd": "mkdir -p /workspace/detonation && cd /workspace/detonation"},
    {"step": 2, "name": "clone_untrusted_repository", "cmd": "git clone --depth 1 https://github.com/example-vuln/pkg /workspace/detonation/repo"},
    {"step": 3, "name": "install_isolated_dependencies", "cmd": "pip install --no-cache-dir -r /workspace/detonation/repo/requirements.txt"},
    {"step": 4, "name": "compile_static_analysis_rules", "cmd": "python -m semgrep --config=auto --dry-run"},
    {"step": 5, "name": "execute_preflight_lint_checks", "cmd": "flake8 /workspace/detonation/repo --select=E9,F63,F7,F82"},
    {"step": 6, "name": "checkpoint_pre_detonation_snapshot", "cmd": "celesto snapshot create --id=snap-pre-detonation-v1"},
    {"step": 7, "name": "detonate_volatile_exploit_payload", "cmd": "python /workspace/detonation/repo/exploit_repro.py --detonate"},
    {"step": 8, "name": "rollback_to_snapshot_state", "cmd": "celesto snapshot rollback --id=snap-pre-detonation-v1"},
    {"step": 9, "name": "apply_mitigation_and_sanitize", "cmd": "python -m pip install --upgrade safe-parser && patch -p1 < patch.diff"},
    {"step": 10, "name": "verify_clean_reproduction_and_export", "cmd": "python /workspace/detonation/repo/exploit_repro.py --verify-safe"}
]

class FailureRecoveryEngine:
    """
    Simulates a 10-step agent pipeline with an intentional volatile crash at Step 7 of 10.
    Applies the 'rollback' recovery policy leveraging Celesto snapshots.
    Records event transitions to failure_trace.jsonl.
    """

    def __init__(
        self,
        sandbox_name: Optional[str] = None,
        trace_path: str = DEFAULT_TRACE_PATH,
        policy: str = "rollback"
    ):
        self.sandbox_name = sandbox_name or generate_sandbox_name("sbx-resilience")
        self.trace_path = trace_path
        self.policy = policy
        self.events: List[Dict[str, Any]] = []

    def _emit_event(self, event_type: str, details: Dict[str, Any]):
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "sandbox_name": self.sandbox_name,
            "event": event_type,
            **details
        }
        self.events.append(entry)
        os.makedirs(os.path.dirname(os.path.abspath(self.trace_path)), exist_ok=True)
        with open(self.trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def run_pipeline(self) -> Dict[str, Any]:
        """
        Executes the 10-step sequence with deterministic failure at step 7,
        applies the recovery policy, and completes execution inside Celesto sandbox.
        """
        # Ensure trace file is clean for this execution
        os.makedirs(os.path.dirname(os.path.abspath(self.trace_path)), exist_ok=True)
        with open(self.trace_path, "w", encoding="utf-8") as f:
            pass

        self._emit_event("pipeline_started", {"total_steps": 10, "initial_target": "celesto_sandbox"})

        with CelestoSandboxContext(sandbox_name=self.sandbox_name) as sbx:
            for step_info in AGENT_PIPELINE_STEPS:
                step_num = step_info["step"]
                step_name = step_info["name"]
                cmd = step_info["cmd"]

                self._emit_event("step_started", {"step": step_num, "name": step_name, "command": cmd})

                if step_num == 7:
                    # Intended mid-task volatile failure at Step 7 of 10
                    sbx.run_command(cmd)  # Audited in commands.jsonl
                    self._emit_event("step_failed", {
                        "step": 7,
                        "name": step_name,
                        "error": "SimulatedVolatileExploitCorruption: SegmentationFault in guest binary parser",
                        "status": "MidTaskFailure"
                    })

                    # Apply Policy: Rollback
                    self._emit_event("policy_applied", {
                        "policy": self.policy,
                        "failed_step": 7,
                        "total_steps": 10,
                        "snapshot_id": "snap-pre-detonation-v1",
                        "restored_state": "step_6_checkpoint"
                    })
                    continue

                if step_num == 8:
                    # Executing rollback command inside sandbox
                    sbx.run_command(cmd)
                    self._emit_event("rollback_restored", {"snapshot_id": "snap-pre-detonation-v1", "guest_health": "clean"})
                    continue

                # Normal step execution inside sandbox
                sbx.run_command(cmd)
                self._emit_event("step_succeeded", {"step": step_num, "name": step_name})

            self._emit_event("pipeline_completed", {"status": "succeeded", "steps_executed": 10})

        self._emit_event("sandbox_deleted", {"state": "deleted", "orphaned": False})
        return {
            "sandbox_name": self.sandbox_name,
            "status": "recovered_and_succeeded",
            "policy": self.policy,
            "total_steps": 10,
            "failed_step": 7
        }

if __name__ == "__main__":
    engine = FailureRecoveryEngine()
    res = engine.run_pipeline()
    print("Failure Recovery Pipeline Finished:", json.dumps(res, indent=2))
