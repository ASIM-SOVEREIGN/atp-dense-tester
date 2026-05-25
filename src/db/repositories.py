"""
Database repository functions for test runs and results
"""

import json
from typing import Optional, List, Dict, Any
from .connection import get_db
from src.models.request import DenseTestRequest

async def create_test_run(task_id: str, request: DenseTestRequest):
    """Create a new test run record"""
    pool = await get_db()
    await pool.execute("""
        INSERT INTO atp_test_runs (task_id, status, config)
        VALUES ($1, 'running', $2)
    """, task_id, json.dumps(request.model_dump()))

async def get_test_run(task_id: str) -> Optional[Dict[str, Any]]:
    """Get a test run by task_id"""
    pool = await get_db()
    row = await pool.fetchrow(
        "SELECT status, config, summary, started_at, completed_at FROM atp_test_runs WHERE task_id = $1",
        task_id
    )
    if not row:
        return None
    
    # Count completed tests
    completed = await pool.fetchval(
        "SELECT COUNT(*) FROM atp_test_results WHERE task_id = $1",
        task_id
    )
    
    config = row["config"] or {}
    total_tests = config.get("total_tests", 0)
    
    return {
        "task_id": task_id,
        "status": row["status"],
        "progress": (completed / total_tests * 100) if total_tests > 0 else 0,
        "total_tests": total_tests,
        "completed_tests": completed or 0,
        "summary": row["summary"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"]
    }

async def get_test_results(task_id: str) -> Optional[List[Dict[str, Any]]]:
    """Get all results for a test run"""
    pool = await get_db()
    rows = await pool.fetch(
        "SELECT sovereign_id, intent_id, outcome, receipt_valid, article_invoked, response_time_ms, reasoning, error_message, created_at FROM atp_test_results WHERE task_id = $1 ORDER BY created_at",
        task_id
    )
    if not rows:
        return None
    return [dict(row) for row in rows]

async def save_test_result(task_id: str, result: Dict[str, Any]):
    """Save a single test result"""
    pool = await get_db()
    await pool.execute("""
        INSERT INTO atp_test_results 
        (task_id, sovereign_id, intent_id, outcome, receipt_valid, 
         article_invoked, response_time_ms, reasoning, error_message)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    """,
        task_id,
        result.get("sovereign_id"),
        result.get("intent_id"),
        result.get("outcome"),
        result.get("receipt_valid"),
        result.get("article_invoked"),
        result.get("response_time_ms"),
        result.get("reasoning"),
        result.get("error_message")
    )

async def update_test_run_summary(task_id: str, summary: Dict[str, Any]):
    """Update test run with completion summary"""
    pool = await get_db()
    await pool.execute("""
        UPDATE atp_test_runs 
        SET status = 'completed', completed_at = NOW(), summary = $1
        WHERE task_id = $2
    """, json.dumps(summary), task_id)
