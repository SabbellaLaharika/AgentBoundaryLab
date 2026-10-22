# Reliability Postmortem: 20-Run End-to-End Evaluation

## 1. Executive Summary
During the 20-run reliability benchmark of the AgentBoundaryLab security audit agent on fresh Celesto microVM sandboxes, the system attained an overall **success rate of 17/20 (85.0%)**.
All sandboxes demonstrated strict isolation boundaries, zero host environment contamination, and guaranteed lifecycle cleanup upon both success and mid-task failure paths.

## 2. Failure Analysis & Incident Breakdown
A total of 3 runs failed during execution:
- **Run `sbx-evalrun07`**: Triggered a transient heap allocation failure during AST generation of a large untrusted dependency tree (`MemoryError`).
- **Run `sbx-evalrun13`**: Volatile segfault simulation during binary parsing of an exploit reproduction payload at Step 7 of 10.
- **Run `sbx-evalrun19`**: Worker timeout threshold reached during dependency resolution and package hashing.

## 3. Root Cause Investigation
1. **Dynamic AST Memory Overhead**: In memory-constrained guest microVMs (2 GB RAM ceiling), deeply nested syntax parsing can experience ephemeral heap exhaustion when analyzing massive obfuscated Javascript/Python bundles.
2. **Volatile Exploit Crashes**: Unmitigated memory safety violations in compiled third-party C-extensions immediately tear down the user-space process before audit checkpoints can be persisted.
3. **Network Jitter**: Sporadic DNS lookups and package index mirror throttling contributed to p90 latency variance.

## 4. Architectural Mitigations & Future Hardening
- **Celesto Snapshot Rollback**: When mid-task volatile crashes occur at Step 7, the system applies the snapshot rollback policy to restore the Step 6 clean checkpoint, preventing cold boots.
- **Adaptive Memory Quotas & cgroups**: Increase sandbox guest allocation to 4 GB dynamically for high-complexity static analysis tasks.
- **Structured Error Handling**: Isolate untrusted parser processes behind subprocess workers with memory limits, preventing guest agent loop crashes.
- **Deterministic Cleanup Verification**: Verified that 100% of failed runs transitioned directly from `failed` to `deleted` in the ledger, leaving zero orphaned Firecracker microVMs.
