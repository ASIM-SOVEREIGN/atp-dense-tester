"""
FastAPI routes for ATP Dense Tester
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from src.models.request import DenseTestRequest, TestStatusResponse
from src.harness.orchestrator import run_test_suite
from src.db.repositories import get_test_run, get_test_results, create_test_run
import uuid

router = APIRouter(prefix="/api/atp", tags=["ATP"])

@router.post("/dense-test")
async def start_dense_test(request: DenseTestRequest, background_tasks: BackgroundTasks):
    """Start a new dense test suite"""
    task_id = str(uuid.uuid4())
    
    await create_test_run(task_id, request)
    
    background_tasks.add_task(
        run_test_suite,
        task_id,
        request,
        {}  # endpoints will be loaded from env
    )
    
    return {"task_id": task_id, "status": "started"}

@router.get("/status/{task_id}", response_model=TestStatusResponse)
async def get_status(task_id: str):
    """Get test progress"""
    run = await get_test_run(task_id)
    if not run:
        raise HTTPException(status_code=404, detail="Task not found")
    return run

@router.get("/results/{task_id}")
async def get_results(task_id: str):
    """Get complete test results"""
    results = await get_test_results(task_id)
    if not results:
        raise HTTPException(status_code=404, detail="No results found")
    return results
