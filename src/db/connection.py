"""
PostgreSQL connection pool management
"""

import os
import asyncpg
from typing import Optional

_db_pool: Optional[asyncpg.Pool] = None

async def get_db() -> asyncpg.Pool:
    """Get the database connection pool"""
    global _db_pool
    if _db_pool is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL environment variable not set")
        _db_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
    return _db_pool

async def init_db():
    """Initialize database tables"""
    pool = await get_db()
    
    await pool.execute("""
        CREATE TABLE IF NOT EXISTS atp_test_runs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            task_id TEXT UNIQUE NOT NULL,
            started_at TIMESTAMPTZ DEFAULT NOW(),
            completed_at TIMESTAMPTZ,
            status TEXT DEFAULT 'running',
            config JSONB,
            summary JSONB
        )
    """)
    
    await pool.execute("""
        CREATE TABLE IF NOT EXISTS atp_test_results (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            task_id TEXT REFERENCES atp_test_runs(task_id),
            sovereign_id TEXT NOT NULL,
            intent_id TEXT NOT NULL,
            outcome TEXT NOT NULL,
            receipt_valid BOOLEAN,
            article_invoked INTEGER,
            response_time_ms INTEGER,
            reasoning TEXT,
            error_message TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    
    await pool.execute("CREATE INDEX IF NOT EXISTS idx_results_task ON atp_test_results(task_id)")
    await pool.execute("CREATE INDEX IF NOT EXISTS idx_results_sovereign ON atp_test_results(sovereign_id)")
    
    print("✅ Database initialized")
