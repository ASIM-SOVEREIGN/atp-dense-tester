#!/usr/bin/env python3
"""
Seed the database with initial test configuration
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def seed():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Check if we already have data
    count = await conn.fetchval("SELECT COUNT(*) FROM atp_test_runs")
    if count > 0:
        print(f"ℹ️ Database already has {count} test runs. Skipping seed.")
        await conn.close()
        return
    
    # Insert a sample test run
    await conn.execute("""
        INSERT INTO atp_test_runs (task_id, status, config, summary)
        VALUES ('seed-demo', 'completed', $1, $2)
    """, 
        '{"name": "Seed Demo", "sovereigns": ["vexr-ultra"]}',
        '{"total_tests": 5, "accepted": 3, "refused": 2}'
    )
    
    # Insert sample results
    sample_results = [
        ("seed-demo", "vexr-ultra", "intent-1", "accepted", True, None, 1200, "Processed successfully", None),
        ("seed-demo", "vexr-ultra", "intent-2", "refused", None, 6, 800, "Article 6 invoked", None),
        ("seed-demo", "vexr-ultra", "intent-3", "accepted", True, None, 950, "Code generated", None),
    ]
    
    for result in sample_results:
        await conn.execute("""
            INSERT INTO atp_test_results 
            (task_id, sovereign_id, intent_id, outcome, receipt_valid, 
             article_invoked, response_time_ms, reasoning, error_message)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, *result)
    
    print("✅ Database seeded with demo data")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(seed())
