import os
import time
import logging
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from src.config import config

logger = logging.getLogger(__name__)

# Fallback in-memory ledger used if Postgres is unavailable (e.g. standalone test mode)
_IN_MEMORY_RUNS: Dict[str, Dict[str, Any]] = {
    "seed-run-001": {
        "run_id": "seed-run-001",
        "sandbox_name": "sbx-seeddemo1",
        "problem_id": "problem-seed-demo",
        "state": "deleted",
        "execution_target": "celesto_sandbox",
        "created_at": "2026-10-20T00:00:00Z",
        "updated_at": "2026-10-20T00:00:00Z"
    }
}

def get_connection():
    try:
        conn = psycopg2.connect(config.DATABASE_URL, connect_timeout=3)
        return conn
    except Exception as e:
        logger.warning(f"Database connection failed ({e}); operating with in-memory fallback.")
        return None

def init_db():
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # Ensure schema exists
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS runs (
                        run_id VARCHAR(128) PRIMARY KEY,
                        sandbox_name VARCHAR(128) NOT NULL,
                        problem_id VARCHAR(128) NOT NULL,
                        state VARCHAR(32) NOT NULL,
                        execution_target VARCHAR(64) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                    INSERT INTO runs (run_id, sandbox_name, problem_id, state, execution_target)
                    VALUES ('seed-run-001', 'sbx-seeddemo1', 'problem-seed-demo', 'deleted', 'celesto_sandbox')
                    ON CONFLICT (run_id) DO NOTHING;
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Error initializing DB schema: {e}")
        finally:
            conn.close()

def get_all_runs() -> List[Dict[str, Any]]:
    conn = get_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT run_id, sandbox_name, problem_id, state, execution_target, created_at, updated_at FROM runs ORDER BY created_at ASC")
                rows = cur.fetchall()
                result = []
                for row in rows:
                    row_dict = dict(row)
                    if row_dict.get("created_at"):
                        row_dict["created_at"] = row_dict["created_at"].isoformat()
                    if row_dict.get("updated_at"):
                        row_dict["updated_at"] = row_dict["updated_at"].isoformat()
                    result.append(row_dict)
                return result
        except Exception as e:
            logger.error(f"Error fetching runs from DB: {e}")
        finally:
            conn.close()
    return list(_IN_MEMORY_RUNS.values())

def insert_run(run: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    stored = {
        **run,
        "created_at": now_iso,
        "updated_at": now_iso
    }
    _IN_MEMORY_RUNS[run["run_id"]] = stored
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO runs (run_id, sandbox_name, problem_id, state, execution_target, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (run_id) DO UPDATE SET
                        state = EXCLUDED.state,
                        updated_at = NOW()
                    RETURNING run_id, sandbox_name, problem_id, state, execution_target, created_at, updated_at;
                """, (run["run_id"], run["sandbox_name"], run["problem_id"], run["state"], run["execution_target"]))
                row = cur.fetchone()
                conn.commit()
                if row:
                    row_dict = dict(row)
                    row_dict["created_at"] = row_dict["created_at"].isoformat() if row_dict.get("created_at") else now_iso
                    row_dict["updated_at"] = row_dict["updated_at"].isoformat() if row_dict.get("updated_at") else now_iso
                    return row_dict
        except Exception as e:
            logger.error(f"Error inserting run into DB: {e}")
        finally:
            conn.close()
    return stored
