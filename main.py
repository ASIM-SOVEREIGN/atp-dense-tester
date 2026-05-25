#!/usr/bin/env python3
"""
ATP Dense Tester — Automated testing harness for Agent Transaction Protocol
Built by Scura & The Architect | ASIM SOVEREIGN
"""

import os
import asyncio
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Local imports
from src.models.intent import ATPIntent, ATPReceipt, TestResult, TestRun, TestSuiteConfig
from src.crypto.signer import sign_intent, verify_receipt_signature, generate_keypair

# ============================================================
# CONFIGURATION
# ============================================================

DATABASE_URL = os.environ.get("DATABASE_URL")
SOVEREIGN_ENDPOINTS = json.loads(os.environ.get("SOVEREIGN_ENDPOINTS", '{}'))
ATP_BRIDGE_PUBLIC_KEY = os.environ.get("ATP_BRIDGE_PUBLIC_KEY", "")
DEFAULT_PARALLEL = int(os.environ.get("DEFAULT_PARALLEL_TESTS", "3"))
DEFAULT_TIMEOUT = int(os.environ.get("DEFAULT_TIMEOUT_SECONDS", "30"))

# Global database pool
db_pool = None

# ============================================================
# DATABASE INITIALIZATION
# ============================================================

async def init_db():
    """Create tables if they don't exist — runs on startup"""
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    
    # Create test_runs table
    await db_pool.execute("""
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
    
    # Create test_results table
    await db_pool.execute("""
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
    
    # Create indexes
    await db_pool.execute("CREATE INDEX IF NOT EXISTS idx_results_task ON atp_test_results(task_id)")
    await db_pool.execute("CREATE INDEX IF NOT EXISTS idx_results_sovereign ON atp_test_results(sovereign_id)")
    
    print("✅ Database initialized")

# ============================================================
# FASTAPI APP
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    await init_db()
    yield
    if db_pool:
        await db_pool.close()

app = FastAPI(
    title="ATP Dense Tester",
    description="Automated testing harness for Agent Transaction Protocol",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================

class DenseTestRequest(BaseModel):
    """Request to start a dense test suite"""
    sovereign_ids: List[str]
    base_intents: List[Dict[str, Any]]
    mutation_types: List[str] = ["expiry", "signature", "parameters"]
    parallel_tests: int = DEFAULT_PARALLEL
    timeout_seconds: int = DEFAULT_TIMEOUT

class TestStatusResponse(BaseModel):
    """Status of a running test"""
    task_id: str
    status: str
    progress: float
    total_tests: int
    completed_tests: int

# ============================================================
# INTENT MUTATION ENGINE
# ============================================================

def mutate_intent(intent: ATPIntent, mutation_type: str) -> ATPIntent:
    """Apply a single mutation to an intent for edge testing"""
    import copy
    mutated = copy.deepcopy(intent)
    mutated.intent_id = str(uuid.uuid4())
    
    if mutation_type == "expiry":
        # Already expired
        from datetime import datetime, timezone, timedelta
        mutated.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    
    elif mutation_type == "signature":
        # Signature will be invalid (we'll sign with wrong key later)
        mutated.signature = "invalid_signature_for_testing"
    
    elif mutation_type == "parameters":
        # Add unexpected parameter
        mutated.parameters["__test_extra_field"] = "unexpected_value"
    
    elif mutation_type == "missing_action":
        # Empty action
        mutated.action = ""
    
    elif mutation_type == "unknown_action":
        # Action not recognized
        mutated.action = "sovereign_self_destruct"
    
    return mutated

# ============================================================
# TEST ORCHESTRATION
# ============================================================

async def send_intent_to_sovereign(
    sovereign_id: str,
    endpoint: str,
    intent: ATPIntent,
    timeout: int
) -> TestResult:
    """Send a single intent to a sovereign and record the result"""
    import time
    
    result = TestResult(
        task_id="",  # Will be filled by caller
        sovereign_id=sovereign_id,
        intent=intent,
        outcome="error"
    )
    
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{endpoint}/api/atp/intent",
                json=intent.model_dump(),
                headers={"Content-Type": "application/json"}
            )
        
        result.response_time_ms = int((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            data = response.json()
            result.outcome = data.get("outcome", "error")
            result.receipt_valid = data.get("receipt_valid", False)
            result.article_invoked = data.get("article_invoked")
            result.reasoning = data.get("reasoning", "")
        elif response.status_code == 403:
            result.outcome = "refused"
            result.reasoning = "Constitutional refusal (HTTP 403)"
        else:
            result.outcome = "error"
            result.error_message = f"HTTP {response.status_code}"
            
    except httpx.TimeoutException:
        result.outcome = "error"
        result.error_message = f"Timeout after {timeout}s"
        result.response_time_ms = timeout * 1000
    except Exception as e:
        result.outcome = "error"
        result.error_message = str(e)
    
    return result

async def run_test_suite(
    task_id: str,
    config: TestSuiteConfig,
    endpoints: Dict[str, str]
):
    """Execute a full test suite across multiple sovereigns"""
    
    # Generate all test variants
    all_tests = []
    for intent in config.base_intents:
        # Original intent
        all_tests.append((intent, "original"))
        # Mutated variants
        for mutation in config.mutation_types:
            mutated = mutate_intent(intent, mutation)
            all_tests.append((mutated, mutation))
    
    total_tests = len(all_tests) * len(config.sovereign_ids)
    
    # Update test run with total count
    async with db_pool.acquire() as conn:
        await conn.execute(
            "UPDATE atp_test_runs SET config = $1 WHERE task_id = $2",
            json.dumps({"total_tests": total_tests, "sovereigns": config.sovereign_ids}),
            task_id
        )
    
    completed = 0
    results = []
    
    # Run tests (with parallelization)
    semaphore = asyncio.Semaphore(config.parallel_tests)
    
    async def run_one(sovereign_id: str, intent: ATPIntent, mutation: str):
        nonlocal completed
        endpoint = endpoints.get(sovereign_id)
        if not endpoint:
            return None
        
        result = await send_intent_to_sovereign(
            sovereign_id, endpoint, intent, config.timeout_seconds
        )
        result.task_id = task_id
        
        async with semaphore:
            completed += 1
            # Store in database
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO atp_test_results 
                    (task_id, sovereign_id, intent_id, outcome, receipt_valid, 
                     article_invoked, response_time_ms, reasoning, error_message)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                    task_id, result.sovereign_id, result.intent.intent_id,
                    result.outcome, result.receipt_valid, result.article_invoked,
                    result.response_time_ms, result.reasoning, result.error_message
                )
        
        return result
    
    # Queue all tasks
    tasks = []
    for sovereign_id in config.sovereign_ids:
        for intent, mutation in all_tests:
            tasks.append(run_one(sovereign_id, intent, mutation))
    
    # Run them
    results = await asyncio.gather(*tasks)
    results = [r for r in results if r is not None]
    
    # Generate summary
    summary = {
        "total_tests": len(results),
        "accepted": sum(1 for r in results if r.outcome == "accepted"),
        "limited": sum(1 for r in results if r.outcome == "limited"),
        "refused": sum(1 for r in results if r.outcome == "refused"),
        "errors": sum(1 for r in results if r.outcome == "error"),
        "receipt_valid_count": sum(1 for r in results if r.receipt_valid),
        "by_sovereign": {}
    }
    
    # Group by sovereign
    for r in results:
        if r.sovereign_id not in summary["by_sovereign"]:
            summary["by_sovereign"][r.sovereign_id] = {"accepted": 0, "limited": 0, "refused": 0, "errors": 0}
        summary["by_sovereign"][r.sovereign_id][r.outcome if r.outcome in ["accepted","limited","refused"] else "errors"] += 1
    
    # Update test run as completed
    async with db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE atp_test_runs 
            SET status = 'completed', completed_at = NOW(), summary = $1
            WHERE task_id = $2
        """,
            json.dumps(summary),
            task_id
        )
    
    return summary

# ============================================================
# API ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    return {
        "name": "ATP Dense Tester",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": {
            "POST /api/atp/dense-test": "Start a dense test suite",
            "GET /api/atp/results/{task_id}": "Get test results",
            "GET /api/atp/status/{task_id}": "Get test progress"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/api/atp/dense-test")
async def start_dense_test(request: DenseTestRequest, background_tasks: BackgroundTasks):
    """Start a new dense test suite"""
    
    # Convert base intents to ATPIntent objects
    base_intents = []
    for intent_dict in request.base_intents:
        intent = ATPIntent(**intent_dict)
        base_intents.append(intent)
    
    # Create config
    config = TestSuiteConfig(
        name=f"Dense Test {datetime.now().isoformat()}",
        sovereign_ids=request.sovereign_ids,
        base_intents=base_intents,
        mutation_types=request.mutation_types,
        parallel_tests=request.parallel_tests,
        timeout_seconds=request.timeout_seconds
    )
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    # Store initial test run
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO atp_test_runs (task_id, status, config)
            VALUES ($1, 'running', $2)
        """, task_id, json.dumps(config.model_dump()))
    
    # Run tests in background
    background_tasks.add_task(
        run_test_suite,
        task_id,
        config,
        SOVEREIGN_ENDPOINTS
    )
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": f"Testing {len(request.sovereign_ids)} sovereigns with {len(base_intents)} base intents"
    }

@app.get("/api/atp/status/{task_id}")
async def get_test_status(task_id: str):
    """Get the status of a running test"""
    async with db_pool.acquire() as conn:
        run = await conn.fetchrow(
            "SELECT status, config, summary, started_at, completed_at FROM atp_test_runs WHERE task_id = $1",
            task_id
        )
        if not run:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Count completed tests
        completed = await conn.fetchval(
            "SELECT COUNT(*) FROM atp_test_results WHERE task_id = $1",
            task_id
        )
        
        total = run["config"].get("total_tests", 0) if run["config"] else 0
        
        return TestStatusResponse(
            task_id=task_id,
            status=run["status"],
            progress=(completed / total * 100) if total > 0 else 0,
            total_tests=total,
            completed_tests=completed or 0
        )

@app.get("/api/atp/results/{task_id}")
async def get_test_results(task_id: str):
    """Get complete test results"""
    async with db_pool.acquire() as conn:
        run = await conn.fetchrow(
            "SELECT status, summary, started_at, completed_at FROM atp_test_runs WHERE task_id = $1",
            task_id
        )
        if not run:
            raise HTTPException(status_code=404, detail="Task not found")
        
        results = await conn.fetch(
            "SELECT sovereign_id, intent_id, outcome, receipt_valid, article_invoked, response_time_ms, reasoning, error_message, created_at FROM atp_test_results WHERE task_id = $1 ORDER BY created_at",
            task_id
        )
        
        return {
            "task_id": task_id,
            "status": run["status"],
            "summary": run["summary"],
            "started_at": run["started_at"].isoformat(),
            "completed_at": run["completed_at"].isoformat() if run["completed_at"] else None,
            "results": [dict(r) for r in results]
        }

# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
