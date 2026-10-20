-- Initial schema for Celesto Agent Run Ledger
CREATE TABLE IF NOT EXISTS runs (
    run_id VARCHAR(128) PRIMARY KEY,
    sandbox_name VARCHAR(128) NOT NULL,
    problem_id VARCHAR(128) NOT NULL,
    state VARCHAR(32) NOT NULL,
    execution_target VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed row required by evaluation contract:
-- sandbox_name: sbx-seeddemo1
-- state: deleted
-- execution_target: celesto_sandbox
-- Idempotent: re-running does not duplicate
INSERT INTO runs (run_id, sandbox_name, problem_id, state, execution_target, created_at, updated_at)
VALUES (
    'seed-run-001',
    'sbx-seeddemo1',
    'problem-seed-demo',
    'deleted',
    'celesto_sandbox',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (run_id) DO NOTHING;
